import pyodbc
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, HTTPException, Query, Request, Depends, status
import time
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
import hashlib
import os
import json
from decimal import Decimal

# Custom JSON encoder to handle Decimal values
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def custom_jsonable_encoder(obj: Any) -> Any:
    """Custom encoder that handles Decimal objects by converting them to floats."""
    if isinstance(obj, dict):
        return {k: custom_jsonable_encoder(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [custom_jsonable_encoder(i) for i in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    # Use the default jsonable_encoder for other types
    return jsonable_encoder(obj)

# Security constants
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"  # Should be stored in env variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
    conn = pyodbc.connect(
       'DSN=fec;UID=informix;PWD=informix;'
    )
    return conn

def get_cached_connection():
    # Removed caching to avoid using stale connections
    return get_connection()


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

@app.get("/get_disponibilita_articoli_commerciali")
async def get_disponibilita_articoli(current_user: TokenData = Depends(get_current_user)):
    """
    Retrieves the availability data for all article codes.
    Protected by token authentication.
    """
    start_time = time.time()
    cursor = None  # Initialize cursor to None
    try:
        conn = get_cached_connection()
        cursor = conn.cursor()
        
        # Prepare the query
        query = '''select * from products_availability where is_hub = 0'''
        
        # Execute the query with the article code parameter
        cursor.execute(query,)        
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
        
        total_time = time.time() - start_time
        print(f"Total execution time: {total_time} seconds")
        
        # Return the results as JSON
        return JSONResponse(content=jsonable_encoder(results))
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            cursor.close()

@app.get("/get_disponibilita_articoli")
async def get_disponibilita_articoli(current_user: TokenData = Depends(get_current_user)):
    """
    Retrieves the availability data for all article codes.
    Protected by token authentication.
    """
    start_time = time.time()
    cursor = None  # Initialize cursor to None
    try:
        conn = get_cached_connection()
        cursor = conn.cursor()
        
        # Prepare the query
        query = '''select * from products_availability where is_hub = 1'''
        
        # Execute the query with the article code parameter
        cursor.execute(query,)        
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
        
        total_time = time.time() - start_time
        print(f"Total execution time: {total_time} seconds")
        
        # Return the results as JSON
        return JSONResponse(content=jsonable_encoder(results))
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            cursor.close()

@app.get("/articles")
async def get_articles(current_user: TokenData = Depends(get_current_user)):
    """
    Efficiently retrieves all articles with their availability data in a single call.
    This endpoint combines the functionality of fetching articles and their availability.
    Protected by token authentication.
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection_from_pool()
        cursor = conn.cursor()
        
        # Check if we have a cached result
        cache_key = "all_articles"
        cached_result = get_from_cache(cache_key)
        if cached_result:
            total_time = time.time() - start_time
            print(f"Returned cached result for articles in {total_time} seconds")
            return JSONResponse(content=cached_result)
        
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
        
        # Create a mapping of article codes to their original data for later merging
        # Standardize keys by trimming whitespace and converting to uppercase
        article_mapping = {}
        shared_code_parts = {}  # Keep track of which individual codes belong to shared codes

        for article in article_data:
            if 'codice' in article and article['codice']:
                article_code = article['codice'].strip().upper()
                
                # Always add the original code to the mapping
                article_mapping[article_code] = article
                
                # If it contains commas, also track the individual parts
                if ',' in article_code:
                    individual_codes = [code.strip().upper() for code in article_code.split(',')]
                    # Remember which parts belong to this shared code
                    shared_code_parts[article_code] = individual_codes
                    
                    # Add individual codes to query separately
                    for ind_code in individual_codes:
                        if ind_code not in article_mapping:  # Don't overwrite existing entries
                            article_copy = article.copy()
                            article_copy['part_of_shared'] = article_code
                            article_mapping[ind_code] = article_copy

        # Use ONLY the individual codes for querying (shared codes won't exist in the DB)
        query_codes = []
        for code in article_mapping:
            # If this is not a shared code (with commas) OR this is an individual part
            if ',' not in code:
                query_codes.append(code)

        # Now use query_codes for the SQL condition
        code_conditions = " OR ".join([f"UPPER(TRIM(amg_code)) = '{code}'" for code in query_codes])
        
        availability_query = f"""
        select TRIM(amg_code) c_articolo, amg_dest d_articolo,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 1) giac_d01,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 20) giac_d20,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 32) giac_d32,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 40) giac_d40,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 48) giac_d48,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 60) giac_d60,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 81) giac_d81,
(select round(dep_qgiai+dep_qcar-dep_qsca+dep_qord+dep_qorp-dep_qpre-dep_qprp,0) from mgdepo 
  where dep_arti = amg_code and dep_code = 1) 
- (select NVL(sum(mpf_qfab), 0) from mpfabbi, mpordil where mpf_ordl = mol_code and mpf_feva = 'N' and mol_stato = 'P'
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
        availability_data = [dict(zip(result_columns, row)) for row in results]
        
        # Create a mapping of article codes to availability data
        # Also standardize these keys to avoid mismatches
        availability_mapping = {}
        for item in availability_data:
            if 'c_articolo' in item and item['c_articolo']:
                # Standardize the code by trimming and converting to uppercase
                std_code = item['c_articolo'].strip().upper()
                availability_mapping[std_code] = item
        
        # Combine the original article data with the availability data
        combined_data = []
        # Track shared codes we've already processed
        processed_shared_codes = set()

        for code, article in article_mapping.items():
            # Check if this is part of a shared code and if we've already processed it
            if 'part_of_shared' in article and article['part_of_shared'] in processed_shared_codes:
                continue
                
            if 'part_of_shared' in article:
                # This is a shared code - we need to aggregate availability data
                shared_code = article['part_of_shared']
                processed_shared_codes.add(shared_code)
                
                # Find all individual codes that are part of this shared code
                shared_components = [c for c in article_mapping.keys() 
                                     if 'part_of_shared' in article_mapping[c] and 
                                        article_mapping[c]['part_of_shared'] == shared_code]
                                        
                # Create a combined item starting with the shared code article
                combined_item = article.copy()
                # Remove the helper field
                combined_item.pop('part_of_shared', None)
                combined_item['codice'] = shared_code  # Restore the original combined code
                
                # Aggregate availability data for all components
                for field in ['giac_d01', 'giac_d20', 'giac_d32', 'giac_d40', 'giac_d48', 
                             'giac_d60', 'giac_d81', 'disp_d01', 'ord_mpp', 'ord_mp', 'ord_mc', 
                             'dom_mc', 'dom_ms', 'dom_msa', 'dom_mss', 'off_mc', 'off_ms', 
                             'off_msa', 'off_mss']:
                    # Sum the values from each component that has availability data
                    combined_item[field] = sum(
                        float(availability_mapping.get(comp, {}).get(field, 0)) 
                        for comp in shared_components 
                        if comp in availability_mapping
                    )
                combined_data.append(combined_item)
            else:
                # Handle regular single codes as before
                if code in availability_mapping:
                    # Create a copy of the original article data
                    combined_item = article.copy()
                    # Add the availability data
                    combined_item.update(availability_mapping[code])
                    combined_data.append(combined_item)
                else:
                    # If we didn't get availability data for this code, still include it but with zeros
                    combined_item = article.copy()
                    # Add empty availability fields
                    for field in ['giac_d01', 'giac_d20', 'giac_d32', 'giac_d40', 'giac_d48', 'giac_d60', 'giac_d81',
                                 'disp_d01', 'ord_mpp', 'ord_mp', 'ord_mc', 'dom_mc', 'dom_ms', 'dom_msa', 'dom_mss',
                                 'off_mc', 'off_ms', 'off_msa', 'off_mss']:
                        combined_item[field] = 0
                    combined_data.append(combined_item)
        
        # Make sure all numeric fields are properly initialized and convert Decimal to float
        for article in combined_data:
            for field in ['giac_d01', 'giac_d20', 'giac_d32', 'giac_d40', 'giac_d48', 'giac_d60', 'giac_d81',
                         'disp_d01', 'ord_mpp', 'ord_mp', 'ord_mc', 'dom_mc', 'dom_ms', 'dom_msa', 'dom_mss',
                         'off_mc', 'off_ms', 'off_msa', 'off_mss']:
                if field not in article or article[field] is None:
                    article[field] = 0
                # Convert Decimal objects to float for JSON serialization
                elif hasattr(article[field], 'as_integer_ratio'):  # Check if it's a Decimal object
                    article[field] = float(article[field])
        
        # Cache the result
        store_in_cache(cache_key, combined_data, ttl=300)  # Cache for 5 minutes
        
        total_time = time.time() - start_time
        print(f"Total execution time for articles: {total_time} seconds")
        
        # Use our custom encoder to handle Decimal objects
        encoded_data = custom_jsonable_encoder(combined_data)
        return JSONResponse(content=encoded_data)
        
    except Exception as e:
        print(f"Error in get_articles: {str(e)}")
        print(f"Error details: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        if cursor is not None:
            cursor.close()
        # No need to close the connection when using a connection pool

# Simple in-memory cache
_cache = {}

def get_connection_from_pool():
    """Get a connection from a connection pool (or create a new one if pool not initialized)"""
    # For simplicity, we're just getting a new connection
    # In a production system, you would implement an actual connection pool
    return get_connection()

def get_from_cache(key):
    """Get a value from the cache if it exists and is not expired"""
    if key in _cache:
        entry = _cache[key]
        if entry['expiry'] > time.time():
            return entry['data']
        else:
            # Clean up expired entries
            del _cache[key]
    return None

def store_in_cache(key, data, ttl=300):
    """Store a value in the cache with an expiration time"""
    expiry = time.time() + ttl
    _cache[key] = {
        'data': data,
        'expiry': expiry
    }

@app.get("/articles_commerciali")
async def get_articles_commerciali(current_user: TokenData = Depends(get_current_user)):
    """
    Efficiently retrieves all commercial articles with their availability data in a single call.
    This endpoint combines the functionality of fetching commercial articles and their availability.
    Protected by token authentication.
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection_from_pool()
        cursor = conn.cursor()
        
        # Check if we have a cached result
        cache_key = "commercial_articles"
        cached_result = get_from_cache(cache_key)
        if cached_result:
            total_time = time.time() - start_time
            print(f"Returned cached result for commercial articles in {total_time} seconds")
            return JSONResponse(content=cached_result)
        
        # 1. First get the list of article codes from products_availability where is_hub = 0
        article_query = "SELECT * FROM products_availability WHERE is_hub = 0"
        cursor.execute(article_query)
        articles = cursor.fetchall()
        
        if not articles:
            return JSONResponse(
                content={"message": "No commercial articles found."},
                status_code=404
            )
        
        # Get the list of article codes
        article_columns = [column[0] for column in cursor.description]
        article_data = [dict(zip(article_columns, article)) for article in articles]
        
        # Debug: Print the first few article codes
        print(f"First 5 article codes from products_availability: {[article.get('codice', 'N/A') for article in article_data[:5]]}")
        
        # Create a mapping of article codes to their original data for later merging
        # Standardize keys by trimming whitespace and converting to uppercase
        article_mapping = {}
        shared_code_parts = {}  # Keep track of which individual codes belong to shared codes

        for article in article_data:
            if 'codice' in article and article['codice']:
                article_code = article['codice'].strip().upper()
                
                # Always add the original code to the mapping
                article_mapping[article_code] = article
                
                # If it contains commas, also track the individual parts
                if ',' in article_code:
                    individual_codes = [code.strip().upper() for code in article_code.split(',')]
                    # Remember which parts belong to this shared code
                    shared_code_parts[article_code] = individual_codes
                    
                    # Add individual codes to query separately
                    for ind_code in individual_codes:
                        if ind_code not in article_mapping:  # Don't overwrite existing entries
                            article_copy = article.copy()
                            article_copy['part_of_shared'] = article_code
                            article_mapping[ind_code] = article_copy

        # Use ONLY the individual codes for querying (shared codes won't exist in the DB)
        query_codes = []
        for code in article_mapping:
            # If this is not a shared code (with commas) OR this is an individual part
            if ',' not in code:
                query_codes.append(code)

        # Now use query_codes for the SQL condition
        code_conditions = " OR ".join([f"UPPER(TRIM(amg_code)) = '{code}'" for code in query_codes])
        
        # Debug: Print the first part of the conditions 
        print(f"Sample of SQL conditions (first 100 chars): {code_conditions[:100]}...")
        
        availability_query = f"""
        select TRIM(amg_code) c_articolo, amg_dest d_articolo,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 1) giac_d01,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 20) giac_d20,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 32) giac_d32,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 40) giac_d40,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 48) giac_d48,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 60) giac_d60,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 81) giac_d81,
(select round(dep_qgiai+dep_qcar-dep_qsca+dep_qord+dep_qorp-dep_qpre-dep_qprp,0) from mgdepo 
  where dep_arti = amg_code and dep_code = 1) 
- (select NVL(sum(mpf_qfab), 0) from mpfabbi, mpordil where mpf_ordl = mol_code and mpf_feva = 'N' and mol_stato = 'P'
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
 
nvl((select sum(occ_qmov-occ_qcon) from ocordic, ocordit where occ_arti = amg_code and oct_stat != 'O' and occ_tipo = oct_tipo and occ_code = oct_code -- and occ_tipo in ('O','P','Q') 
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
        and ({code_conditions})
        """
        
        cursor.execute(availability_query)
        results = cursor.fetchall()
        
        # Debug: Print number of availability results found
        print(f"Availability query returned {len(results)} rows")
        
        # Get column names and convert to list of dictionaries
        result_columns = [column[0] for column in cursor.description]
        availability_data = [dict(zip(result_columns, row)) for row in results]
        
        # Create a mapping of article codes to availability data
        # Also standardize these keys to avoid mismatches
        availability_mapping = {}
        for item in availability_data:
            if 'c_articolo' in item and item['c_articolo']:
                # Standardize the code by trimming and converting to uppercase
                std_code = item['c_articolo'].strip().upper()
                availability_mapping[std_code] = item
                
        # Debug: Print the first few article codes from availability data
        avail_codes = list(availability_mapping.keys())
        print(f"First 5 article codes from availability: {avail_codes[:5] if avail_codes else 'None'}")
        
        # Debug: Check for key overlaps
        overlap_count = sum(1 for code in article_mapping if code in availability_mapping)
        print(f"Found {overlap_count} articles with matching availability data out of {len(article_mapping)} total articles")
        
        # Combine the original article data with the availability data
        combined_data = []
        # Track shared codes we've already processed
        processed_shared_codes = set()

        for code, article in article_mapping.items():
            # Check if this is part of a shared code and if we've already processed it
            if 'part_of_shared' in article and article['part_of_shared'] in processed_shared_codes:
                continue
                
            if 'part_of_shared' in article:
                # This is a shared code - we need to aggregate availability data
                shared_code = article['part_of_shared']
                processed_shared_codes.add(shared_code)
                
                # Find all individual codes that are part of this shared code
                shared_components = [c for c in article_mapping.keys() 
                                     if 'part_of_shared' in article_mapping[c] and 
                                        article_mapping[c]['part_of_shared'] == shared_code]
                                        
                # Create a combined item starting with the shared code article
                combined_item = article.copy()
                # Remove the helper field
                combined_item.pop('part_of_shared', None)
                combined_item['codice'] = shared_code  # Restore the original combined code
                
                # Aggregate availability data for all components
                for field in ['giac_d01', 'giac_d20', 'giac_d32', 'giac_d40', 'giac_d48', 
                             'giac_d60', 'giac_d81', 'disp_d01', 'ord_mpp', 'ord_mp', 'ord_mc', 
                             'dom_mc', 'dom_ms', 'dom_msa', 'dom_mss', 'off_mc', 'off_ms', 
                             'off_msa', 'off_mss']:
                    # Sum the values from each component that has availability data
                    combined_item[field] = sum(
                        float(availability_mapping.get(comp, {}).get(field, 0)) 
                        for comp in shared_components 
                        if comp in availability_mapping
                    )
                combined_data.append(combined_item)
            else:
                # Handle regular single codes as before
                if code in availability_mapping:
                    # Create a copy of the original article data
                    combined_item = article.copy()
                    # Add the availability data
                    combined_item.update(availability_mapping[code])
                    combined_data.append(combined_item)
                else:
                    # If we didn't get availability data for this code, still include it but with zeros
                    combined_item = article.copy()
                    # Add empty availability fields
                    for field in ['giac_d01', 'giac_d20', 'giac_d32', 'giac_d40', 'giac_d48', 'giac_d60', 'giac_d81',
                                 'disp_d01', 'ord_mpp', 'ord_mp', 'ord_mc', 'dom_mc', 'dom_ms', 'dom_msa', 'dom_mss',
                                 'off_mc', 'off_ms', 'off_msa', 'off_mss']:
                        combined_item[field] = 0
                    combined_data.append(combined_item)
        
        # Make sure all numeric fields are properly initialized and convert Decimal to float
        for article in combined_data:
            for field in ['giac_d01', 'giac_d20', 'giac_d32', 'giac_d40', 'giac_d48', 'giac_d60', 'giac_d81',
                         'disp_d01', 'ord_mpp', 'ord_mp', 'ord_mc', 'dom_mc', 'dom_ms', 'dom_msa', 'dom_mss',
                         'off_mc', 'off_ms', 'off_msa', 'off_mss']:
                if field not in article or article[field] is None:
                    article[field] = 0
                # Convert Decimal objects to float for JSON serialization
                elif hasattr(article[field], 'as_integer_ratio'):  # Check if it's a Decimal object
                    article[field] = float(article[field])
        
        # Cache the result
        store_in_cache(cache_key, combined_data, ttl=300)  # Cache for 5 minutes
        
        total_time = time.time() - start_time
        print(f"Total execution time for commercial articles: {total_time} seconds")
        
        # Use our custom encoder to handle Decimal objects
        encoded_data = custom_jsonable_encoder(combined_data)
        return JSONResponse(content=encoded_data)
        
    except Exception as e:
        print(f"Error in get_articles_commerciali: {str(e)}")
        print(f"Error details: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        if cursor is not None:
            cursor.close()
        # No need to close the connection when using a connection pool

def get_article_history_query():
    # SQL query with placeholders for the article code
    return """
select mpf_arti, f.amg_desc mpf_desc, f.amg_grum, gf.gmg_desc, 
       mpf_qfab * gol_qord / mol_quaor totale, 
       (mpf_qfab-mpf_qpre)* gol_qord / mol_quaor residuo, 
       mol_parte, p.amg_desc mol_desc, 
       occ_tipo, occ_code, occ_riga, occ_dtco, oct_cocl, des_clifor,
       oct_stap
from mpfabbi, mpordil, mpordgol, ocordic, ocordit, agclifor, mganag f, mganag p, mggrum gf
where mpf_ordl = mol_code
and mol_code = gol_mpco
and gol_octi = occ_tipo and gol_occo = occ_code and gol_ocri = occ_riga
and oct_tipo = occ_tipo and oct_code = occ_code
and oct_cocl = cod_clifor
and mpf_arti = f.amg_code and f.amg_grum = gf.gmg_code
and mol_parte = p.amg_code
and mpf_feva = 'N'
and mpf_arti = ?
union all
select occ_arti, f.amg_desc mpf_desc, f.amg_grum, gf.gmg_desc, 
       occ_qmov, occ_qmov-occ_qcon residuo, 
       '' mol_parte, '' mol_desc, 
       occ_tipo, occ_code, occ_riga, occ_dtco, oct_cocl, des_clifor,
       oct_stap
from ocordic, ocordit, agclifor, mganag f, mggrum gf
where oct_tipo = occ_tipo and oct_code = occ_code
and oct_cocl = cod_clifor
and occ_arti = f.amg_code and f.amg_grum = gf.gmg_code
and occ_feva = 'N'
and occ_arti = ?
union all
select mpf_arti, f.amg_desc mpf_desc, f.amg_grum, gf.gmg_desc, 
       mpf_qfab, (mpf_qfab-mpf_qpre) residuo, 
       mol_parte, p.amg_desc mol_desc, 
       "OQ", 0, 0, mpf_dfab, 'ND', 'ORDINE QUADRO',
       '' as oct_stap
from mpfabbi, mpordil, mganag f, mganag p, mggrum gf
where mpf_ordl = mol_code
and mpf_arti = f.amg_code and f.amg_grum = gf.gmg_code
and mol_parte = p.amg_code
and mpf_feva = 'N'
and mpf_ordl = 1
and mpf_arti = ?
ORDER BY occ_dtco asc
    """
@app.get("/article_history")
async def get_article_history(article_code: str, current_user: TokenData = Depends(get_current_user)):
    start_time = time.time()
    cursor = None  # Initialize cursor to None
    try:
        conn = get_connection_from_pool()
        cursor = conn.cursor()

        # Check if we have a cached result
        cache_key = f"article_history_{article_code}"
        cached_result = get_from_cache(cache_key)
        if cached_result:
            total_time = time.time() - start_time
            print(f"Returned cached result for article history in {total_time} seconds")
            return JSONResponse(content=cached_result)

        query = get_article_history_query()

        # Execute the query with the article code parameter
        # Since the article code is used three times due to UNION ALL, we need to provide it three times
        params = (article_code, article_code, article_code)
        cursor.execute(query, params)

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

        # Convert any Decimal values to floats
        for result in results:
            for key, value in result.items():
                if isinstance(value, Decimal):
                    result[key] = float(value)

        # Cache the result
        store_in_cache(cache_key, results, ttl=300)  # Cache for 5 minutes

        total_time = time.time() - start_time
        print(f"Total execution time for article history: {total_time} seconds")

        # Return the results using our custom encoder
        encoded_results = custom_jsonable_encoder(results)
        return JSONResponse(content=encoded_results)

    except Exception as e:
        print(f"Error in get_article_history: {str(e)}")
        print(f"Error details: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        if cursor is not None:
            cursor.close()
        # No need to close the connection when using a connection pool