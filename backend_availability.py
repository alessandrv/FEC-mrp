import pyodbc
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, HTTPException, Query, Request, Depends, status
import time
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
import hashlib
import os
from dotenv import load_dotenv
from contextlib import contextmanager
import decimal

# Load environment variables
load_dotenv()

# Security constants - load from environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Database connection configuration
DB_CONFIG = {
    'DSN': os.getenv('DB_DSN', 'fec'),
    'UID': os.getenv('DB_UID', 'informix'),
    'PWD': os.getenv('DB_PWD', 'informix'),
    'POOL_SIZE': int(os.getenv('DB_POOL_SIZE', '10')),
}

# Connection pool
connection_pool = []

# Result caching system
cache: Dict[str, Dict[str, Any]] = {}

def get_cached_result(key: str) -> Optional[Any]:
    """
    Get a result from the cache if it exists and is not expired.
    """
    if key in cache:
        cache_entry = cache[key]
        if datetime.now() < cache_entry['expires']:
            return cache_entry['data']
        else:
            # Cache expired, remove it
            del cache[key]
    return None

def cache_result(key: str, data: Any, ttl_seconds: int = 300):
    """
    Cache a result with a specific TTL.
    """
    cache[key] = {
        'data': data,
        'expires': datetime.now() + timedelta(seconds=ttl_seconds)
    }

def clear_cache():
    """
    Clear all cached results.
    """
    cache.clear()

@contextmanager
def get_connection_from_pool():
    """Get a connection from the pool and return it when done."""
    conn = None
    try:
        if not connection_pool:
            # If pool is empty, create a new connection
            conn = pyodbc.connect(
                f'DSN={DB_CONFIG["DSN"]};UID={DB_CONFIG["UID"]};PWD={DB_CONFIG["PWD"]};'
            )
        else:
            # Get a connection from the pool
            conn = connection_pool.pop()
        
        yield conn
    except Exception as e:
        print(f"Connection error: {e}")
        # If there was an error with this connection, don't return it to the pool
        if conn:
            try:
                conn.close()
            except:
                pass
            conn = None
        raise
    finally:
        # Return the connection to the pool if it's still valid
        if conn:
            try:
                # Test if connection is still good
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                connection_pool.append(conn)
            except:
                # Connection is bad, close it
                try:
                    conn.close()
                except:
                    pass

# Token and user models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Create OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password validation function
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # In a real scenario, use a proper password hashing library like bcrypt
    # This is a simplified example using SHA-256
    hashed_input = hashlib.sha256(plain_password.encode()).hexdigest()
    return hashed_input == hashed_password

# User authentication
def authenticate_user(username: str, password: str, is_commercial: bool = False) -> bool:
    # Hardcoded hash for 'FecHUB' - in production, use a proper user database
    hashed_password = "6273196ddfee0839909882a24007dde8461b4c99ae2e106ccaca239e74cf2afd"
    
    # If checking for commercial access, use the commercial hash
    if is_commercial:
        hashed_password = COMMERCIALI_HASHED_PASSWORD
    
    if username != "admin":
        return False
    return verify_password(password, hashed_password)

# Create access token
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Token verification dependency
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    return token_data

# After the existing TOKEN_DATA code but before the app creation
# Add a password hash for "FECItalia2025"
COMMERCIALI_HASHED_PASSWORD = "eee94ac6be05824f57abf3c0bd2b46385c477ec78ff8fac7088d5ca8659e4edc"  # SHA-256 hash of "FECItalia2025"

# Import products availability CRUD router

app = FastAPI()

# Add products availability CRUD router

# Configure CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Initialize the connection pool
    await initialize_connection_pool()
    print("Authentication API started and connection pool initialized")

# Login endpoint to get token
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user_authenticated = authenticate_user(form_data.username, form_data.password, is_commercial=False)
    if not user_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Add a password validation endpoint for the frontend
@app.post("/validate_password")
async def validate_password(request: Request):
    try:
        data = await request.json()
        password = data.get("password", "")
        
        # Use the same authentication function with is_commercial=False
        is_valid = authenticate_user("admin", password, is_commercial=False)
        
        return {"valid": is_valid}
    except Exception as e:
        print(f"Error validating password: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Login endpoint to get token
@app.post("/tokenCommerciali", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user_authenticated = authenticate_user(form_data.username, form_data.password, is_commercial=True)
    if not user_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Add a validation endpoint specifically for commercial password
@app.post("/validate_commerciali_password")
async def validate_commerciali_password(request: Request):
    try:
        data = await request.json()
        password = data.get("password", "")
        
        # Use the same authentication function with is_commercial=True
        is_valid = authenticate_user("admin", password, is_commercial=True)
        
        return {"valid": is_valid}
    except Exception as e:
        print(f"Error validating commercial password: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def get_connection():
    """Legacy function to maintain compatibility."""
    conn = pyodbc.connect(
       f'DSN={DB_CONFIG["DSN"]};UID={DB_CONFIG["UID"]};PWD={DB_CONFIG["PWD"]};'
    )
    return conn

def get_cached_connection():
    """Legacy function to maintain compatibility."""
    # For now, still create a new connection to avoid changing logic elsewhere
    # Better approach is to migrate all code to use get_connection_from_pool
    return get_connection()

async def initialize_connection_pool():
    """Initialize the connection pool with a set number of connections."""
    print(f"Initializing connection pool with {DB_CONFIG['POOL_SIZE']} connections for authentication")
    for _ in range(DB_CONFIG['POOL_SIZE']):
        try:
            conn = pyodbc.connect(
                f'DSN={DB_CONFIG["DSN"]};UID={DB_CONFIG["UID"]};PWD={DB_CONFIG["PWD"]};'
            )
            connection_pool.append(conn)
        except Exception as e:
            print(f"Error creating connection: {e}")
    print(f"Authentication connection pool initialized with {len(connection_pool)} connections")

def get_disponibilita_query():
    # Informix-specific optimization hints
    return """

select amg_code c_articolo, amg_dest d_articolo,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 1) giac_d01,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 20) giac_d20,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 32) giac_d32,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 40) giac_d40,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 48) giac_d48,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 60) giac_d60,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 81) giac_d81,
(select round(dep_qgiai+dep_qcar-dep_qsca+dep_qord+dep_qorp-dep_qpre-dep_qprp,0) from mgdepo 
  where dep_arti = amg_code and dep_code = 1) 
- (select sum(mpf_qfab) from mpfabbi, mpordil where mpf_ordl = mol_code and mpf_feva = 'N' and mol_stato = 'P'
and mpf_arti = amg_code)
disp_d01,
nvl((select sum(occ_qmov) from ocordic, ocordit where occ_arti = amg_code -- and occ_tipo in ('O','P','Q')
  and occ_tipo = oct_tipo and occ_code = oct_code
  and oct_data between last_day(add_months(today,-3))+1 and last_day(add_months(today,-2))),0) +
nvl((select sum(mpf_qfab) from mpfabbi, mpordil where mpf_arti = amg_code 
  and mpf_ordl = mol_code and mol_code not in (select gol_mpco from mpordgol)
  and mol_dati between last_day(add_months(today,-3))+1 and last_day(add_months(today,-2))),0) + 
nvl((select sum(mpf_qfab) from mpfabbi, mpordil, mpordgol, ocordit where mpf_arti = amg_code 
  and mpf_ordl = mol_code and mol_code = gol_mpco and gol_octi = oct_tipo and gol_occo = oct_code
  and oct_data between last_day(add_months(today,-3))+1 and last_day(add_months(today,-2))),0) ord_mpp,
nvl((select sum(occ_qmov) from ocordic, ocordit where occ_arti = amg_code --and occ_tipo in ('O','P','Q') 
  and occ_tipo = oct_tipo and occ_code = oct_code
  and oct_data between last_day(add_months(today,-2))+1 and last_day(add_months(today,-1))),0) +
nvl((select sum(mpf_qfab) from mpfabbi, mpordil where mpf_arti = amg_code 
  and mpf_ordl = mol_code and mol_code not in (select gol_mpco from mpordgol)
  and mol_dati between last_day(add_months(today,-2))+1 and last_day(add_months(today,-1))),0) + 
nvl((select sum(mpf_qfab) from mpfabbi, mpordil, mpordgol, ocordit where mpf_arti = amg_code 
  and mpf_ordl = mol_code and mol_code = gol_mpco and gol_octi = oct_tipo and gol_occo = oct_code
  and oct_data between last_day(add_months(today,-2))+1 and last_day(add_months(today,-1))),0) ord_mp,
nvl((select sum(occ_qmov) from ocordic, ocordit where occ_arti = amg_code -- and occ_tipo in ('O','P','Q') 
  and occ_tipo = oct_tipo and occ_code = oct_code
  and oct_data between last_day(add_months(today,-1))+1 and last_day(today)),0) +
nvl((select sum(mpf_qfab) from mpfabbi, mpordil where mpf_arti = amg_code 
  and mpf_ordl = mol_code and mol_code not in (select gol_mpco from mpordgol)
  and mol_dati between last_day(add_months(today,-1))+1 and last_day(today)),0) + 
nvl((select sum(mpf_qfab) from mpfabbi, mpordil, mpordgol, ocordit where mpf_arti = amg_code 
  and mpf_ordl = mol_code and mol_code = gol_mpco and gol_octi = oct_tipo and gol_occo = oct_code
  and oct_data between last_day(add_months(today,-1))+1 and last_day(today)),0) ord_mc,
nvl((select sum(occ_qmov-occ_qcon) from ocordic, ocordit where occ_arti = amg_code and oct_stat != 'O' and occ_tipo = oct_tipo and occ_code = oct_code -- and occ_tipo in ('O','P','Q') 
and occ_feva = 'N'
  and occ_dtco <= last_day(today)),0) +
nvl((select sum(mpf_qfab-mpf_qpre) from mpfabbi where mpf_arti = amg_code and mpf_feva = 'N'
  and mpf_dfab <= last_day(today)),0) dom_mc,
nvl((select sum(occ_qmov-occ_qcon) from ocordic, ocordit where occ_arti = amg_code and oct_stat != 'O' and occ_tipo = oct_tipo and occ_code = oct_code --and occ_tipo in ('O','P','Q') 
and occ_feva = 'N'
  and occ_dtco between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))),0) +
nvl((select sum(mpf_qfab-mpf_qpre) from mpfabbi where mpf_arti = amg_code and mpf_feva = 'N'
  and mpf_dfab between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))),0) dom_ms,
 
nvl((select sum(occ_qmov-occ_qcon) from ocordic, ocordit where occ_arti = amg_code and oct_stat != 'O' and occ_tipo = oct_tipo and occ_code = oct_code --and occ_tipo in ('O','P','Q') 
and occ_feva = 'N'
  and occ_dtco between last_day(add_months(today,+1))+1 and last_day(add_months(today,+2))),0) +
nvl((select sum(mpf_qfab-mpf_qpre) from mpfabbi where mpf_arti = amg_code and mpf_feva = 'N'
  and mpf_dfab between last_day(add_months(today,+1))+1 and last_day(add_months(today,+2))),0) dom_msa,  
 
nvl((select sum(occ_qmov-occ_qcon) from ocordic, ocordit where occ_arti = amg_code and oct_stat != 'O' and occ_tipo = oct_tipo and occ_code = oct_code -- and occ_tipo in ('O','P','Q') 
and occ_feva = 'N'
  and occ_dtco >= last_day(add_months(today,+2))+1),0) +
nvl((select sum(mpf_qfab-mpf_qpre) from mpfabbi where mpf_arti = amg_code and mpf_feva = 'N'
  and mpf_dfab >= last_day(add_months(today,+2))+1),0) dom_mss,
nvl((select sum(ofc_qord-ofc_qcon) from ofordic where ofc_arti = amg_code and ofc_feva = 'N'
  and ofc_dtco <= last_day(today)),0) +
nvl((select sum(mol_quaor-mol_quari) from mpordil where mol_parte = amg_code and mol_stato in ('A')
  and mol_dats <= last_day(today)),0) off_mc,
nvl((select sum(ofc_qord-ofc_qcon) from ofordic where ofc_arti = amg_code and ofc_feva = 'N'
  and ofc_dtco between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))),0) +
nvl((select sum(mol_quaor-mol_quari) from mpordil where mol_parte = amg_code and mol_stato in ('A')
  and mol_dats between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))),0) off_ms,
 
nvl((select sum(ofc_qord-ofc_qcon) from ofordic where ofc_arti = amg_code and ofc_feva = 'N'
  and ofc_dtco between last_day(add_months(today,+1))+1 and last_day(add_months(today,+2))),0) +
nvl((select sum(mol_quaor-mol_quari) from mpordil where mol_parte = amg_code and mol_stato in ('A')
  and mol_dats between last_day(add_months(today,+1))+1 and last_day(add_months(today,+2))),0) off_msa,
 
nvl((select sum(ofc_qord-ofc_qcon) from ofordic where ofc_arti = amg_code and ofc_feva = 'N'
  and ofc_dtco >= last_day(add_months(today,2))+1),0) +
nvl((select sum(mol_quaor-mol_quari) from mpordil where mol_parte = amg_code and mol_stato in ('A')
  and mol_dats >= last_day(add_months(today,2))+1),0) off_mss
from mganag, mppoli
where amg_code = amp_code and amp_depo = 1
and  amg_stat = 'D' 
and nvl(amg_fagi,'S') = 'S'

and amg_code = ?
    """

@app.get("/article_disponibilita")
async def get_article_disponibilita(article_code: str, current_user: TokenData = Depends(get_current_user)):
    """
    Retrieves the availability data for a specific article code.
    Protected by token authentication.
    """
    # Try to get results from cache first (cache for 5 minutes)
    CACHE_TTL = int(os.getenv('ARTICLE_DISPONIBILITA_CACHE_TTL_SECONDS', '300'))
    cache_key = f"article_disponibilita_{article_code}"
    cached_data = get_cached_result(cache_key)
    
    if cached_data:
        return JSONResponse(content=cached_data)
    
    start_time = time.time()
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            # Prepare the query
            query = get_disponibilita_query()
            
            # Execute the query with the article code parameter
            cursor.execute(query, (article_code,))
            
            # Fetch all results
            rows = cursor.fetchall()
            
            # Check if any rows were returned
            if not rows:
                return JSONResponse(
                    content={"message": "Article not found."},
                    status_code=404
                )
            
            # Convert the results to a list of dictionaries
            columns = [column[0] for column in cursor.description]
            results = [dict(zip(columns, row)) for row in rows]
            
            # Encode results for cache and response
            encoded_results = jsonable_encoder(results)
            
            # Cache the result
            cache_result(cache_key, encoded_results, CACHE_TTL)
            
            total_time = time.time() - start_time
            print(f"Article disponibilita execution time: {total_time} seconds")
            
            # Return the results as JSON
            return JSONResponse(content=encoded_results)
        
    except Exception as e:
        print(f"Error in article_disponibilita: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/get_disponibilita_articoli_commerciali")
async def get_disponibilita_articoli(current_user: TokenData = Depends(get_current_user)):
    """
    Retrieves the availability data for all article codes.
    Protected by token authentication.
    """
    # Try to get results from cache first (cache for 5 minutes)
    CACHE_TTL = int(os.getenv('ARTICOLI_COMMERCIALI_CACHE_TTL_SECONDS', '300'))
    cache_key = "disponibilita_articoli_commerciali"
    cached_data = get_cached_result(cache_key)
    
    if cached_data:
        return JSONResponse(content=cached_data)
    
    start_time = time.time()
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            # Prepare the query
            query = '''select * from products_availability where is_hub = 0'''
            
            # Execute the query
            cursor.execute(query)
            
            # Fetch all results
            rows = cursor.fetchall()
            
            # Check if any rows were returned
            if not rows:
                return JSONResponse(
                    content={"message": "Articles not found."},
                    status_code=404
                )
            
            # Convert the results to a list of dictionaries
            columns = [column[0] for column in cursor.description]
            results = [dict(zip(columns, row)) for row in rows]
            
            # Encode results for cache and response
            encoded_results = jsonable_encoder(results)
            
            # Cache the result
            cache_result(cache_key, encoded_results, CACHE_TTL)
            
            total_time = time.time() - start_time
            print(f"Articoli commerciali execution time: {total_time} seconds")
            
            # Return the results as JSON
            return JSONResponse(content=encoded_results)
        
    except Exception as e:
        print(f"Error in get_disponibilita_articoli_commerciali: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/articoli")
async def get_disponibilita_articoli(current_user: TokenData = Depends(get_current_user)):
    """
    Fetches the availability data for regular articles.
    Protected by token authentication.
    """
    # Try to get results from cache first (cache for 5 minutes)
    CACHE_TTL = int(os.getenv('ARTICLES_AVAILABILITY_CACHE_TTL_SECONDS', '300'))
    cache_key = "disponibilita_articoli"
    cached_data = get_cached_result(cache_key)
    
    if cached_data:
        return JSONResponse(content=cached_data)
    
    start_time = time.time()
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM products_availability WHERE is_hub = 1"
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                return JSONResponse(
                    content={"message": "No articles found."},
                    status_code=404
                )
            
            # Get the column names from cursor description
            columns = [column[0] for column in cursor.description]
            
            # Convert to list of dictionaries
            articles = [dict(zip(columns, row)) for row in results]
            
            # Encode results for cache and response
            encoded_results = jsonable_encoder(articles)
            
            # Cache the result
            cache_result(cache_key, encoded_results, CACHE_TTL)
            
            total_time = time.time() - start_time
            print(f"Articles availability execution time: {total_time} seconds")
            
            return JSONResponse(content=encoded_results)
        
    except Exception as e:
        print(f"Error in get_disponibilita_articoli: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/articles")
async def get_articles(current_user: TokenData = Depends(get_current_user)):
    """
    Efficiently retrieves all articles with their availability data in a single call.
    This endpoint combines the functionality of fetching articles and their availability.
    Protected by token authentication.
    """
    # Try to get results from cache first (cache for 5 minutes)
    CACHE_TTL = int(os.getenv('ARTICLES_AVAILABILITY_CACHE_TTL_SECONDS', '300'))
    cache_key = "all_articles_availability"
    cached_data = get_cached_result(cache_key)
    
    if cached_data:
        return JSONResponse(content=cached_data)
    
    start_time = time.time()
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            # 1. First get the list of article codes from products_availability where is_hub = 1
            article_query = "SELECT * FROM products_availability WHERE is_hub = 1"
            cursor.execute(article_query)
            articles = cursor.fetchall()
            
            if not articles:
                return JSONResponse(
                    content={"message": "No articles found."},
                    status_code=404
                )
            
            # Get the list of article codes
            article_columns = [column[0] for column in cursor.description]
            article_data = [dict(zip(article_columns, article)) for article in articles]
            
            # Extract article codes and create the OR condition for the next query
            article_codes = [article['codice'] for article in article_data if 'codice' in article]
            
            if not article_codes:
                return JSONResponse(
                    content={"message": "No valid article codes found."},
                    status_code=404
                )
            
            # 2. Build a single query to get availability data for all articles at once
            # Create the OR condition part of the query
            code_conditions = " OR ".join([f"amg_code = '{code}'" for code in article_codes])
            
            availability_query = f"""
            select amg_code c_articolo, amg_dest d_articolo,
    (select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 1) giac_d01,
    (select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 20) giac_d20,
    (select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 32) giac_d32,
    (select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 40) giac_d40,
    (select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 48) giac_d48,
    (select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 60) giac_d60,
    (select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 81) giac_d81,
    (select round(dep_qgiai+dep_qcar-dep_qsca+dep_qord+dep_qorp-dep_qpre-dep_qprp,0) from mgdepo 
      where dep_arti = amg_code and dep_code = 1) 
    - (select sum(mpf_qfab) from mpfabbi, mpordil where mpf_ordl = mol_code and mpf_feva = 'N' and mol_stato = 'P'
    and mpf_arti = amg_code)
    disp_d01,
    nvl((select sum(occ_qmov) from ocordic, ocordit where occ_arti = amg_code -- and occ_tipo in ('O','P','Q')
      and occ_tipo = oct_tipo and occ_code = oct_code
      and oct_data between last_day(add_months(today,-3))+1 and last_day(add_months(today,-2))),0) +
    nvl((select sum(mpf_qfab) from mpfabbi, mpordil where mpf_arti = amg_code 
      and mpf_ordl = mol_code and mol_code not in (select gol_mpco from mpordgol)
      and mol_dati between last_day(add_months(today,-3))+1 and last_day(add_months(today,-2))),0) + 
    nvl((select sum(mpf_qfab) from mpfabbi, mpordil, mpordgol, ocordit where mpf_arti = amg_code 
      and mpf_ordl = mol_code and mol_code = gol_mpco and gol_octi = oct_tipo and gol_occo = oct_code
      and oct_data between last_day(add_months(today,-3))+1 and last_day(add_months(today,-2))),0) ord_mpp,
    nvl((select sum(occ_qmov) from ocordic, ocordit where occ_arti = amg_code --and occ_tipo in ('O','P','Q') 
      and occ_tipo = oct_tipo and occ_code = oct_code
      and oct_data between last_day(add_months(today,-2))+1 and last_day(add_months(today,-1))),0) +
    nvl((select sum(mpf_qfab) from mpfabbi, mpordil where mpf_arti = amg_code 
      and mpf_ordl = mol_code and mol_code not in (select gol_mpco from mpordgol)
      and mol_dati between last_day(add_months(today,-2))+1 and last_day(add_months(today,-1))),0) + 
    nvl((select sum(mpf_qfab) from mpfabbi, mpordil, mpordgol, ocordit where mpf_arti = amg_code 
      and mpf_ordl = mol_code and mol_code = gol_mpco and gol_octi = oct_tipo and gol_occo = oct_code
      and oct_data between last_day(add_months(today,-2))+1 and last_day(add_months(today,-1))),0) ord_mp,
    nvl((select sum(occ_qmov) from ocordic, ocordit where occ_arti = amg_code -- and occ_tipo in ('O','P','Q') 
      and occ_tipo = oct_tipo and occ_code = oct_code
      and oct_data between last_day(add_months(today,-1))+1 and last_day(today)),0) +
    nvl((select sum(mpf_qfab) from mpfabbi, mpordil where mpf_arti = amg_code 
      and mpf_ordl = mol_code and mol_code not in (select gol_mpco from mpordgol)
      and mol_dati between last_day(add_months(today,-1))+1 and last_day(today)),0) + 
    nvl((select sum(mpf_qfab) from mpfabbi, mpordil, mpordgol, ocordit where mpf_arti = amg_code 
      and mpf_ordl = mol_code and mol_code = gol_mpco and gol_octi = oct_tipo and gol_occo = oct_code
      and oct_data between last_day(add_months(today,-1))+1 and last_day(today)),0) ord_mc,
    nvl((select sum(occ_qmov-occ_qcon) from ocordic, ocordit where occ_arti = amg_code and oct_stat != 'O' and occ_tipo = oct_tipo and occ_code = oct_code -- and occ_tipo in ('O','P','Q') 
    and occ_feva = 'N'
      and occ_dtco <= last_day(today)),0) +
    nvl((select sum(mpf_qfab-mpf_qpre) from mpfabbi where mpf_arti = amg_code and mpf_feva = 'N'
      and mpf_dfab <= last_day(today)),0) dom_mc,
    nvl((select sum(occ_qmov-occ_qcon) from ocordic, ocordit where occ_arti = amg_code and oct_stat != 'O' and occ_tipo = oct_tipo and occ_code = oct_code --and occ_tipo in ('O','P','Q') 
    and occ_feva = 'N'
      and occ_dtco between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))),0) +
    nvl((select sum(mpf_qfab-mpf_qpre) from mpfabbi where mpf_arti = amg_code and mpf_feva = 'N'
      and mpf_dfab between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))),0) dom_ms,
     
    nvl((select sum(occ_qmov-occ_qcon) from ocordic, ocordit where occ_arti = amg_code and oct_stat != 'O' and occ_tipo = oct_tipo and occ_code = oct_code --and occ_tipo in ('O','P','Q') 
    and occ_feva = 'N'
      and occ_dtco between last_day(add_months(today,+1))+1 and last_day(add_months(today,+2))),0) +
    nvl((select sum(mpf_qfab-mpf_qpre) from mpfabbi where mpf_arti = amg_code and mpf_feva = 'N'
      and mpf_dfab between last_day(add_months(today,+1))+1 and last_day(add_months(today,+2))),0) dom_msa,  
     
    nvl((select sum(occ_qmov-occ_qcon) from ocordic, ocordit where occ_arti = amg_code and oct_stat != 'O' and occ_tipo = oct_tipo and occ_code = oct_code -- and occ_tipo in ('O','P','Q') 
    and occ_feva = 'N'
      and occ_dtco >= last_day(add_months(today,+2))+1),0) +
    nvl((select sum(mpf_qfab-mpf_qpre) from mpfabbi where mpf_arti = amg_code and mpf_feva = 'N'
      and mpf_dfab >= last_day(add_months(today,+2))+1),0) dom_mss,
    nvl((select sum(ofc_qord-ofc_qcon) from ofordic where ofc_arti = amg_code and ofc_feva = 'N'
      and ofc_dtco <= last_day(today)),0) +
    nvl((select sum(mol_quaor-mol_quari) from mpordil where mol_parte = amg_code and mol_stato in ('A')
      and mol_dats <= last_day(today)),0) off_mc,
    nvl((select sum(ofc_qord-ofc_qcon) from ofordic where ofc_arti = amg_code and ofc_feva = 'N'
      and ofc_dtco between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))),0) +
    nvl((select sum(mol_quaor-mol_quari) from mpordil where mol_parte = amg_code and mol_stato in ('A')
      and mol_dats between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))),0) off_ms,
     
    nvl((select sum(ofc_qord-ofc_qcon) from ofordic where ofc_arti = amg_code and ofc_feva = 'N'
      and ofc_dtco between last_day(add_months(today,+1))+1 and last_day(add_months(today,+2))),0) +
    nvl((select sum(mol_quaor-mol_quari) from mpordil where mol_parte = amg_code and mol_stato in ('A')
      and mol_dats between last_day(add_months(today,+1))+1 and last_day(add_months(today,+2))),0) off_msa,
     
    nvl((select sum(ofc_qord-ofc_qcon) from ofordic where ofc_arti = amg_code and ofc_feva = 'N'
      and ofc_dtco >= last_day(add_months(today,2))+1),0) +
    nvl((select sum(mol_quaor-mol_quari) from mpordil where mol_parte = amg_code and mol_stato in ('A')
      and mol_dats >= last_day(add_months(today,2))+1),0) off_mss
    from mganag, mppoli
    where amg_code = amp_code and amp_depo = 1
    and amg_stat = 'D' 
    and nvl(amg_fagi,'S') = 'S'
            and ({code_conditions})
            """
            
            cursor.execute(availability_query)
            results = cursor.fetchall()
            
            if not results:
                return JSONResponse(
                    content={"message": "No availability data found for articles."},
                    status_code=404
                )
            
            # Get column names and convert to list of dictionaries
            result_columns = [column[0] for column in cursor.description]
            final_data = [dict(zip(result_columns, row)) for row in results]
            
            # Make sure all numeric fields are properly initialized
            for article in final_data:
                for field in ['giac_d01', 'giac_d20', 'giac_d32', 'giac_d40', 'giac_d48', 'giac_d60', 'giac_d81',
                             'ord_mpp', 'ord_mp', 'ord_mc', 'dom_mc', 'dom_ms', 'dom_msa', 'dom_mss',
                             'off_mc', 'off_ms', 'off_msa', 'off_mss']:
                    if field not in article or article[field] is None:
                        article[field] = 0
            
            # Encode results for cache and response
            encoded_results = jsonable_encoder(final_data)
            
            # Cache the result
            cache_result(cache_key, encoded_results, CACHE_TTL)
            
            total_time = time.time() - start_time
            print(f"Articles availability execution time: {total_time} seconds")
            
            return JSONResponse(content=encoded_results)
        
    except Exception as e:
        print(f"Error in get_articles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/articles_commerciali")
async def get_disponibilita_articoli_commerciali(current_user: TokenData = Depends(get_current_user_commerciali)):
    """
    Fetches the availability data for commercial articles.
    Protected by commercial token authentication.
    """
    # Try to get results from cache first (cache for 5 minutes)
    CACHE_TTL = int(os.getenv('ARTICLES_COMM_AVAILABILITY_CACHE_TTL_SECONDS', '300'))
    cache_key = "disponibilita_articoli_commerciali"
    cached_data = get_cached_result(cache_key)
    
    if cached_data:
        return JSONResponse(content=cached_data)
    
    start_time = time.time()
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM products_availability WHERE is_hub = 0"
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                return JSONResponse(
                    content={"message": "No commercial articles found."},
                    status_code=404
                )
            
            # Get the column names from cursor description
            columns = [column[0] for column in cursor.description]
            
            # Convert to list of dictionaries
            articles = [dict(zip(columns, row)) for row in results]
            
            # Encode results for cache and response
            encoded_results = jsonable_encoder(articles)
            
            # Cache the result
            cache_result(cache_key, encoded_results, CACHE_TTL)
            
            total_time = time.time() - start_time
            print(f"Commercial articles availability execution time: {total_time} seconds")
            
            return JSONResponse(content=encoded_results)
        
    except Exception as e:
        print(f"Error in get_disponibilita_articoli_commerciali: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

def get_article_history_query():
    """
    Returns the SQL query for getting article history data.
    """
    return """
    SELECT 
        'ORDINE CLIENTE' as tipo,
        to_char(oct_data, 'YYYY-MM-DD') as data,
        nvl(tes_ragsoc, 'SCONOSCIUTO') as riferimento,
        oct_note as note,
        occ_qmov as quantita
    FROM 
        ocordit, ocordic, testate
    WHERE 
        oct_code = occ_code AND
        oct_tipo = occ_tipo AND
        tes_code = oct_clie AND
        occ_arti = :article_code
        
    UNION ALL
        
    SELECT 
        'ORDINE FORNITORE' as tipo,
        to_char(oft_data, 'YYYY-MM-DD') as data,
        nvl(tes_ragsoc, 'SCONOSCIUTO') as riferimento,
        oft_note as note,
        ofc_qord as quantita
    FROM 
        ofordit, ofordic, testate
    WHERE 
        oft_code = ofc_code AND
        oft_tipo = ofc_tipo AND
        tes_code = oft_forn AND
        ofc_arti = :article_code
        
    UNION ALL
        
    SELECT 
        'ORDINE DI PRODUZIONE' as tipo,
        to_char(mpo_data, 'YYYY-MM-DD') as data,
        nvl(mol_note, 'NESSUNA NOTA') as riferimento,
        mpo_note as note,
        mol_quaor as quantita
    FROM 
        mpordil, mpordit
    WHERE 
        mol_ordit = mpo_code AND
        mol_parte = :article_code
    
    ORDER BY
        data DESC
    """

@app.get("/article_history")
async def get_article_history(codice: str, current_user: TokenData = Depends(get_current_user)):
    """
    Fetches the history data for a specific article.
    Protected by token authentication.
    """
    # Try to get results from cache first (cache for 5 minutes)
    CACHE_TTL = int(os.getenv('ARTICLE_HISTORY_CACHE_TTL_SECONDS', '300'))
    cache_key = f"article_history_{codice}"
    cached_data = get_cached_result(cache_key)
    
    if cached_data:
        return JSONResponse(content=cached_data)
    
    start_time = time.time()
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            # Get the query for article history
            query = get_article_history_query()
            
            # Execute the query with named bind variables
            cursor.execute(query, article_code=codice)
            results = cursor.fetchall()
            
            if not results:
                return JSONResponse(
                    content={"message": f"No history found for article: {codice}"},
                    status_code=404
                )
            
            # Get column names and convert to list of dictionaries
            columns = [column[0] for column in cursor.description]
            history_data = [dict(zip(columns, row)) for row in results]
            
            # Format dates and numbers for better readability
            for item in history_data:
                for key, value in item.items():
                    if isinstance(value, datetime.date):
                        item[key] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (decimal.Decimal, float)):
                        item[key] = float(value)
            
            # Encode results for cache and response
            encoded_results = jsonable_encoder(history_data)
            
            # Cache the result
            cache_result(cache_key, encoded_results, CACHE_TTL)
            
            total_time = time.time() - start_time
            print(f"Article history execution time for {codice}: {total_time} seconds")
            
            return JSONResponse(content=encoded_results)
        
    except Exception as e:
        print(f"Error in get_article_history for {codice}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.post("/simulate_order")
async def simulate_order(items: list, period: str = "today", current_user: TokenData = Depends(get_current_user)):
    """
    Simulates an order based on the provided items and returns the availability results.
    The period parameter determines which time period to evaluate for availability:
    - "today": Current day
    - "mc": Current month
    - "ms": Next month
    - "msa": Two months ahead
    - "mss": Beyond two months
    """
    if not items:
        raise HTTPException(status_code=400, detail="No items provided for simulation")
    
    start_time = time.time()
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            # Validate all article codes exist before simulation
            item_codes = [item.get('article_code') for item in items if item.get('article_code')]
            if not item_codes:
                raise HTTPException(status_code=400, detail="No valid article codes provided")
            
            # Create a placeholders string for SQL IN clause
            placeholders = ', '.join(f"'{code}'" for code in item_codes)
            
            # Check if articles exist
            validation_query = f"""
            SELECT amg_code, amg_dest 
            FROM mganag 
            WHERE amg_code IN ({placeholders})
            """
            
            cursor.execute(validation_query)
            existing_articles = cursor.fetchall()
            
            if len(existing_articles) != len(item_codes):
                existing_codes = [row[0] for row in existing_articles]
                missing_codes = [code for code in item_codes if code not in existing_codes]
                raise HTTPException(
                    status_code=400, 
                    detail=f"The following article codes do not exist: {', '.join(missing_codes)}"
                )
            
            # Create a mapping of code to description
            code_to_desc = {row[0]: row[1] for row in existing_articles}
            
            # Get current availability for these articles
            if period == "today":
                availability_field = "disp_d01"
            elif period == "mc":
                availability_field = "dom_mc"
            elif period == "ms":
                availability_field = "dom_ms"
            elif period == "msa":
                availability_field = "dom_msa"
            elif period == "mss":
                availability_field = "dom_mss"
            else:
                availability_field = "disp_d01"  # Default to today
                
            availability_query = f"""
            SELECT c_articolo, 
                   d_articolo, 
                   {availability_field} AS current_availability
            FROM products_availability 
            WHERE c_articolo IN ({placeholders})
            """
            
            cursor.execute(availability_query)
            availability_results = cursor.fetchall()
            
            # Create availability mapping: code -> current availability
            availability_map = {row[0]: float(row[2] if row[2] is not None else 0) 
                              for row in availability_results}
            
            # For articles not found in products_availability, set availability to 0
            for code in item_codes:
                if code not in availability_map:
                    availability_map[code] = 0
            
            # Process each item and calculate the simulated availability
            simulation_results = []
            
            for item in items:
                code = item.get('article_code')
                quantity = float(item.get('quantity', 0))
                
                if not code or quantity <= 0:
                    continue
                
                current_avail = availability_map.get(code, 0)
                simulated_avail = current_avail - quantity
                
                # Determine status based on availability
                status = "OK" if simulated_avail >= 0 else "INSUFFICIENT"
                
                # Add to results
                simulation_results.append({
                    "article_code": code,
                    "description": code_to_desc.get(code, "Unknown"),
                    "requested_quantity": quantity,
                    "current_availability": current_avail,
                    "simulated_availability": simulated_avail,
                    "status": status,
                    "parent_codes": []  # Placeholder for parent codes if needed
                })
            
            # Sort results by status (INSUFFICIENT first) then by code
            simulation_results.sort(
                key=lambda x: (0 if x["status"] == "INSUFFICIENT" else 1, x["article_code"])
            )
            
            total_time = time.time() - start_time
            print(f"Order simulation execution time: {total_time} seconds")
            
            return JSONResponse(content=jsonable_encoder({
                "simulation_period": period,
                "results": simulation_results
            }))
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Error in simulate_order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")