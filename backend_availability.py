import pyodbc
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, HTTPException, Query, Request, Depends, status
import time
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
import hashlib

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
def authenticate_user(username: str, password: str) -> bool:
    # Hardcoded hash for 'FecHUB' - in production, use a proper user database
    hashed_password = "6273196ddfee0839909882a24007dde8461b4c99ae2e106ccaca239e74cf2afd"
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
    user_authenticated = authenticate_user(form_data.username, form_data.password)
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
        
        # You could use the same authentication function
        is_valid = authenticate_user("admin", password)
        
        return {"valid": is_valid}
    except Exception as e:
        print(f"Error validating password: {str(e)}")
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
and amg_code in (select dep_arti from mgdepo where dep_code in (1,20,32,48,60,81)
and dep_qgiai+dep_qcar-dep_qsca+dep_qord+dep_qorp+dep_qpre+dep_qprp <> 0)
and amg_code = ?
    """

@app.get("/article_disponibilita")
async def get_article_disponibilita(article_code: str, current_user: TokenData = Depends(get_current_user)):
    """
    Retrieves the availability data for a specific article code.
    Protected by token authentication.
    """
    start_time = time.time()
    cursor = None  # Initialize cursor to None
    try:
        conn = get_cached_connection()
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

