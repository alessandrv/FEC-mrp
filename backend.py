import pyodbc
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
import json
import time
from functools import lru_cache
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import List, Dict, Any, Optional
import asyncio
import os
from dotenv import load_dotenv
from contextlib import contextmanager
from datetime import datetime, timedelta
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Import products availability CRUD router
import products_availability_crud

app = FastAPI()

origins = [
    "http://172.16.16.27:3000",
    "http://localhost:3000",
]
extra = os.getenv("BACKEND_CORS_ORIGINS")
if extra:
    origins.extend([o.strip() for o in extra.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Database connection configuration
DB_CONFIG = {
    'DSN': os.getenv('DB_DSN', 'fec'),
    'UID': os.getenv('DB_UID', 'informix'),
    'PWD': os.getenv('DB_PWD', 'informix'),
    'POOL_SIZE': int(os.getenv('DB_POOL_SIZE', '10')),
}

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

async def cache_cleanup_task():
    """
    Periodically clean up expired cache entries.
    """
    while True:
        now = datetime.now()
        keys_to_remove = []
        
        # Find expired cache entries
        for key, entry in cache.items():
            if now > entry['expires']:
                keys_to_remove.append(key)
        
        # Remove expired entries
        for key in keys_to_remove:
            del cache[key]
        
        # Log cleanup stats
        if keys_to_remove:
            print(f"Cache cleanup: removed {len(keys_to_remove)} expired entries. Cache size: {len(cache)}")
        
        # Sleep for 5 minutes
        await asyncio.sleep(300)

# Connection pool
connection_pool = []
pool_lock = asyncio.Lock()

async def initialize_connection_pool():
    """Initialize the connection pool with a set number of connections."""
    print(f"Initializing connection pool with {DB_CONFIG['POOL_SIZE']} connections")
    for _ in range(DB_CONFIG['POOL_SIZE']):
        try:
            conn = pyodbc.connect(
                f'DSN={DB_CONFIG["DSN"]};UID={DB_CONFIG["UID"]};PWD={DB_CONFIG["PWD"]};'
            )
            connection_pool.append(conn)
        except Exception as e:
            print(f"Error creating connection: {e}")
    print(f"Connection pool initialized with {len(connection_pool)} connections")

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

today_orders_query = '''
select t.oct_data, t.oct_tipo, t.oct_code, t.oct_cocl, c.des_clifor,
  r.occ_riga, r.occ_arti, trim(r.occ_desc)||' '||trim(nvl(r.occ_des2,' ')) as descrizione, r.occ_qmov-r.occ_qcon qty,
  r.occ_dtco,
 
nvl((select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = occ_arti and dep_code = 1), 0) Stock,
 
nvl((select sum(ofc_qord-ofc_qcon) from ofordic where ofc_arti = occ_arti and ofc_feva = 'N'
  and ofc_dtco <= last_day(today)),0) +
nvl((select sum(mol_quaor-mol_quari) from mpordil where mol_parte = occ_arti and mol_stato in ('A')
  and mol_dats <= last_day(today)),0) ArrMonth,
nvl((select sum(ofc_qord-ofc_qcon) from ofordic where ofc_arti = occ_arti and ofc_feva = 'N'
  and ofc_dtco between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))),0) +
nvl((select sum(mol_quaor-mol_quari) from mpordil where mol_parte = occ_arti and mol_stato in ('A')
  and mol_dats between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))),0) ArrNextMonth,
 
nvl((select sum(ofc_qord-ofc_qcon) from ofordic where ofc_arti = occ_arti and ofc_feva = 'N'
  and ofc_dtco >= last_day(add_months(today,1))+1),0) +
nvl((select sum(mol_quaor-mol_quari) from mpordil where mol_parte = occ_arti and mol_stato in ('A')
  and mol_dats >= last_day(add_months(today,1))+1),0) ArrFollowing
 
from ocordit t, ocordic r, agclifor c
where t.oct_cocl = c.cod_clifor
and t.oct_tipo = r.occ_tipo and t.oct_code = r.occ_code
and t.oct_stat = 'A'
and r.occ_feva = 'N' -- non evaso
and r.occ_arti != '' and r.occ_arti != 'CONAI' and r.occ_arti not like 'EG%'
and t.oct_toco = 'VEN'
and t.oct_data = TODAY
order by occ_dtco ASC
'''

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



def get_optimized_query():
    # Informix-specific optimization hints
    return """
select amg_code c_articolo, amg_dest d_articolo, amg_tipo a_p, amp_lead lt,
nvl((select round(dep_scom) from mgdepo where dep_arti = amg_code and dep_code = 1),0) scrt,
(select min(cf.des_clifor) from ofordic ofc
 join ofordit oft on ofc.ofc_tipo = oft.oft_tipo and ofc.ofc_code = oft.oft_code
 join agclifor cf on oft.oft_cofo = cf.cod_clifor
 where ofc.ofc_arti = amg_code  
 and ofc.ofc_dtco = (select max(ofc2.ofc_dtco) from ofordic ofc2 where ofc2.ofc_arti = amg_code)) fornitore,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 1) giac_d01,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 20) giac_d20,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 32) giac_d32,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 40) giac_d40,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 48) giac_d48,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 60) giac_d60,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 80) giac_d80,
(select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = amg_code and dep_code = 81) giac_d81,
nvl((select sum(mpl.mpl_coimp * 
    (select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = mpl.mpl_padre and dep_code = 81)
  ) from mplegami mpl where mpl.mpl_figlio = amg_code),0) giac_d81_legami,
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
  and mol_dats >= last_day(add_months(today,2))+1),0) off_mss,
-- New domanda logic based on ocordic/ocordit with active orders (oct_stat = 'A')
-- Includes both direct demand and indirect demand from parent articles
nvl((
  -- Direct demand for the main article (current month)
  select sum(occ_qmov) from ocordic oc
  inner join ocordit ot on oc.occ_tipo = ot.oct_tipo and oc.occ_code = ot.oct_code
  where oc.occ_arti = amg_code and ot.oct_stat = 'A' and oc.occ_feva = "N"
  and oc.occ_dtco <= last_day(today)
),0) +
nvl((
  -- Indirect demand from parent articles (current month)
  select sum(occ_qmov * mpl.mpl_coimp) from mplegami mpl
  inner join ocordic oc on oc.occ_arti = mpl.mpl_padre
  inner join ocordit ot on oc.occ_tipo = ot.oct_tipo and oc.occ_code = ot.oct_code
  where mpl.mpl_figlio = amg_code and ot.oct_stat = 'A' and oc.occ_feva = "N"
  and oc.occ_dtco <= last_day(today)
),0) domanda_mc,
nvl((
  -- Direct demand for the main article (next month)
  select sum(occ_qmov) from ocordic oc
  inner join ocordit ot on oc.occ_tipo = ot.oct_tipo and oc.occ_code = ot.oct_code
  where oc.occ_arti = amg_code and ot.oct_stat = 'A' and oc.occ_feva = "N"
  and oc.occ_dtco between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))
),0) +
nvl((
  -- Indirect demand from parent articles (next month)
  select sum(occ_qmov * mpl.mpl_coimp) from mplegami mpl
  inner join ocordic oc on oc.occ_arti = mpl.mpl_padre
  inner join ocordit ot on oc.occ_tipo = ot.oct_tipo and oc.occ_code = ot.oct_code
  where mpl.mpl_figlio = amg_code and ot.oct_stat = 'A' and oc.occ_feva = "N"
  and oc.occ_dtco between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))
),0) domanda_ms,
nvl((
  -- Direct demand for the main article (2 months successor)
  select sum(occ_qmov) from ocordic oc
  inner join ocordit ot on oc.occ_tipo = ot.oct_tipo and oc.occ_code = ot.oct_code
  where oc.occ_arti = amg_code and ot.oct_stat = 'A' and oc.occ_feva = "N"
  and oc.occ_dtco between last_day(add_months(today,+1))+1 and last_day(add_months(today,+2))
),0) +
nvl((
  -- Indirect demand from parent articles (2 months successor)
  select sum(occ_qmov * mpl.mpl_coimp) from mplegami mpl
  inner join ocordic oc on oc.occ_arti = mpl.mpl_padre
  inner join ocordit ot on oc.occ_tipo = ot.oct_tipo and oc.occ_code = ot.oct_code
  where mpl.mpl_figlio = amg_code and ot.oct_stat = 'A' and oc.occ_feva = "N"
  and oc.occ_dtco between last_day(add_months(today,+1))+1 and last_day(add_months(today,+2))
),0) domanda_msa,
nvl((
  -- Direct demand for the main article (3+ months successor)
  select sum(occ_qmov) from ocordic oc
  inner join ocordit ot on oc.occ_tipo = ot.oct_tipo and oc.occ_code = ot.oct_code
  where oc.occ_arti = amg_code and ot.oct_stat = 'A' and oc.occ_feva = "N"
  and oc.occ_dtco >= last_day(add_months(today,+2))+1
),0) +
nvl((
  -- Indirect demand from parent articles (3+ months successor)
  select sum(occ_qmov * mpl.mpl_coimp) from mplegami mpl
  inner join ocordic oc on oc.occ_arti = mpl.mpl_padre
  inner join ocordit ot on oc.occ_tipo = ot.oct_tipo and oc.occ_code = ot.oct_code
  where mpl.mpl_figlio = amg_code and ot.oct_stat = 'A' and oc.occ_feva = "N"
  and oc.occ_dtco >= last_day(add_months(today,+2))+1
),0) domanda_mss,
-- Last purchase date from supplier orders (excluding type 'O')
( select max(oft.oft_data)
  from ofordic ofc
  join ofordit oft on ofc.ofc_tipo = oft.oft_tipo and ofc.ofc_code = oft.oft_code
  where ofc.ofc_arti = amg_code
    and ofc.ofc_tipo != 'O'
) last_purchase
from mganag, mppoli
where amg_code = amp_code and amp_depo = 1
and  amg_stat = 'D' 
and nvl(amg_fagi,'S') = 'S'
    """

def get_article_price_query():
    # SQL query with a placeholder for the article code
    return """
    SELECT
        t.oft_data AS date,
        c.ofc_preu AS price,
        c.ofc_qord AS quantity,
        t.oft_valu AS valuta
    FROM
        ofordic c
        INNER JOIN ofordit t ON c.ofc_code = t.oft_code
    WHERE
        c.ofc_arti = ?
        AND c.ofc_tipo != 'O'
    ORDER BY
        t.oft_data ASC
        
    """
def get_price_difference_percentage_query():
    return """
SELECT DISTINCT
    c1.ofc_arti AS article_code,
    MIN(c1.ofc_preu) AS min_price,
    MAX(c1.ofc_preu) AS max_price,
    ROUND(((MAX(c1.ofc_preu) - MIN(c1.ofc_preu)) / MIN(c1.ofc_preu) * 100), 2) AS price_increase_percent,
    MIN(t1.oft_data) AS first_order_date,
    MAX(t1.oft_data) AS last_order_date
FROM
    ofordic c1
    INNER JOIN ofordit t1 ON c1.ofc_code = t1.oft_code
WHERE
    c1.ofc_tipo != 'O'
    AND c1.ofc_preu > 0
GROUP BY
    c1.ofc_arti
HAVING
    ((MAX(c1.ofc_preu) - MIN(c1.ofc_preu)) / MIN(c1.ofc_preu) * 100) >= 100
ORDER BY
    price_increase_percent DESC
"""
def get_fifo_price_query():
    # SQL query to get FIFO price data from mpcosdat table
    return """
    SELECT
        cod_data AS date,
        cod_vald AS price
    FROM
        mpcosdat
    WHERE
        cod_arti = ?
        AND cod_voce = 99
        AND cod_tipo = 'FIF'
    ORDER BY
        cod_data ASC
    """

def get_current_cost_query():
    # SQL query to get current cost data from mpcosti table
    return """
    SELECT
        coa_data AS date,
        coa_vald AS price,
        coa_tipo AS cost_type
    FROM
        mpcosti
    WHERE
        coa_arti = ?
        AND coa_voce = 99
        AND (coa_tipo = 'FIF' OR coa_tipo = 'EFF')
    ORDER BY
        coa_data DESC
    """

@app.get("/articles")
async def get_articles():
    """
    Get all articles with availability information.
    This is a high-traffic endpoint, so we cache the results.
    """
    # Try to get results from cache first (cache for 5 minutes)
    CACHE_TTL = int(os.getenv('ARTICLES_CACHE_TTL_SECONDS', '300'))
    cache_key = "all_articles"
    cached_data = get_cached_result(cache_key)
    
    
    
    # If not in cache, fetch from database
    start_time = time.time()
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            query = get_optimized_query()
            
            # Measure query execution time
            query_start = time.time()
            cursor.execute(query)
            query_execution_time = time.time() - query_start
            print(f"Query execution time: {query_execution_time} seconds")
            
            # Measure data fetching time
            fetch_start = time.time()
            rows = cursor.fetchall()
            fetch_time = time.time() - fetch_start
            print(f"Data fetch time: {fetch_time} seconds")
            
            # Measure data processing time
            process_start = time.time()
            columns = [column[0] for column in cursor.description]
            results = [dict(zip(columns, row)) for row in rows]
            processing_time = time.time() - process_start
            print(f"Data processing time: {processing_time} seconds")
            
            # Measure serialization time
            serialize_start = time.time()
            json_content = json.dumps(results, default=str)
            serialization_time = time.time() - serialize_start
            print(f"Serialization time: {serialization_time} seconds")
            
            # Cache the serialized result
            cache_result(cache_key, json_content, CACHE_TTL)
            
            total_time = time.time() - start_time
            print(f"Total execution time: {total_time} seconds")
            
            return Response(
                content=json_content,
                media_type="application/json"
            )
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

@app.get("/article_price")
async def get_article_price(article_code: str):
    """
    Get price history for a specific article.
    """
    # Try to get results from cache first (cache for 15 minutes)
    CACHE_TTL = int(os.getenv('ARTICLE_PRICE_CACHE_TTL_SECONDS', '900'))
    cache_key = f"article_price_{article_code}"
    cached_data = get_cached_result(cache_key)
    
    if cached_data:
        return JSONResponse(content=cached_data)
    
    start_time = time.time()
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            # Get main price data
            query = get_article_price_query()
            cursor.execute(query, (article_code,))
            rows = cursor.fetchall()
            
            # Get FIFO price data from mpcosdat
            fifo_query = get_fifo_price_query()
            
            # Get current cost data from mpcosti
            cost_query = get_current_cost_query()
            
            # Check if any main price rows were returned
            if not rows:
                return JSONResponse(
                    content={"message": "Article not found."},
                    status_code=404
                )
            
            # Convert the main results to a list of dictionaries
            columns = [column[0] for column in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in rows
            ]
            
            # Process FIFO data
            cursor.execute(fifo_query, (article_code,))
            fifo_columns = [column[0] for column in cursor.description]
            fifo_results = [
                dict(zip(fifo_columns, row))
                for row in cursor.fetchall()
            ]
            
            # Process cost data
            cursor.execute(cost_query, (article_code,))
            cost_columns = [column[0] for column in cursor.description]
            cost_results = [
                dict(zip(cost_columns, row))
                for row in cursor.fetchall()
            ]
            
            # Process data on the backend
            from collections import defaultdict
            from datetime import datetime

            # Prepare raw data
            rawData = []
            valuta = results[0]['valuta']
            for item in results:
                # Ensure the date is in ISO format
                date_obj = item['date']
                if isinstance(date_obj, datetime):
                    date_str = date_obj.isoformat()
                else:
                    date_str = str(date_obj)

                rawData.append({
                    'date': date_str,
                    'price': float(item['price']),
                    'quantity': float(item['quantity']),
                    'valuta': item['valuta'],
                })
            
            # Prepare FIFO data
            fifoData = []
            for item in fifo_results:
                # Ensure the date is in ISO format
                date_obj = item['date']
                if isinstance(date_obj, datetime):
                    date_str = date_obj.isoformat()
                else:
                    date_str = str(date_obj)

                fifoData.append({
                    'date': date_str,
                    'price': float(item['price']),
                })
            
            # Sort FIFO data by date
            fifoData.sort(key=lambda x: x['date'])
            
            # Process cost data
            currentFifoCost = None
            currentEffCost = None
            
            for item in cost_results:
                # Ensure the date is in ISO format
                date_obj = item['date']
                if isinstance(date_obj, datetime):
                    date_str = date_obj.isoformat()
                else:
                    date_str = str(date_obj)
                
                if item['cost_type'] == 'FIF' and currentFifoCost is None:
                    currentFifoCost = {
                        'date': date_str,
                        'price': float(item['price']),
                    }
                elif item['cost_type'] == 'EFF' and currentEffCost is None:
                    currentEffCost = {
                        'date': date_str,
                        'price': float(item['price']),
                    }
                
                # Stop after finding both types
                if currentFifoCost and currentEffCost:
                    break
            
            # Sort rawData by date
            rawData.sort(key=lambda x: x['date'])
            
            # Compute average data per month
            monthlyDataMap = defaultdict(lambda: {'total': 0, 'count': 0})
            for item in rawData:
                # Extract 'YYYY-MM' from date
                month = item['date'][:7]
                monthlyDataMap[month]['total'] += item['price']
                monthlyDataMap[month]['count'] += 1
            
            averageData = []
            for month, data in monthlyDataMap.items():
                averageData.append({
                    'date': month,
                    'price': data['total'] / data['count'],
                })
            
            # Sort averageData by date
            averageData.sort(key=lambda x: x['date'])
            
            # Compute max and min price data
            maxPriceData = max(rawData, key=lambda x: x['price'])
            minPriceData = min(rawData, key=lambda x: x['price'])
            
            # Prepare the response
            response = {
                'rawData': rawData,
                'averageData': averageData,
                'fifoData': fifoData,
                'currentFifoCost': currentFifoCost,
                'currentEffCost': currentEffCost,
                'valuta': valuta,
                'maxPriceData': maxPriceData,
                'minPriceData': minPriceData,
            }
            
            # Encode the response
            encoded_response = jsonable_encoder(response)
            
            # Cache the result
            cache_result(cache_key, encoded_response, CACHE_TTL)
            
            total_time = time.time() - start_time
            print(f"Total execution time: {total_time} seconds")
            
            return JSONResponse(content=encoded_response)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

@app.get("/article_history")
async def get_article_history(article_code: str):
    """
    Get article history for a specific article.
    """
    # Try to get results from cache first (cache for 10 minutes)
    CACHE_TTL = int(os.getenv('ARTICLE_HISTORY_CACHE_TTL_SECONDS', '600'))
    cache_key = f"article_history_{article_code}"
    cached_data = get_cached_result(cache_key)
    
    if cached_data:
        return JSONResponse(content=cached_data)
        
    start_time = time.time()
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()

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

            # Encode the results
            encoded_results = jsonable_encoder(results)
            
            # Cache the results
            cache_result(cache_key, encoded_results, CACHE_TTL)

            total_time = time.time() - start_time
            print(f"Total execution time: {total_time} seconds")

            # Return the results as JSON
            return JSONResponse(content=encoded_results)

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"Client disconnected: {websocket.client}")

    async def broadcast(self, message: str):
        print(f"Broadcasting message to {len(self.active_connections)} clients.")
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error sending message to {connection.client}: {e}")

manager = ConnectionManager()

@app.websocket("/ws/articles")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection open
            data = await websocket.receive_text()
            print(f"Received message from client: {data}")
            # Optionally handle incoming messages from clients
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

from fastapi import BackgroundTasks

@app.on_event("startup")
async def startup_event():
    # Initialize the connection pool
    await initialize_connection_pool()
    
    # Start the broadcast task in the background
    asyncio.create_task(broadcast_articles_periodically())
    
    # Start the cache cleanup task
    asyncio.create_task(cache_cleanup_task())
    
    # Create products_availability table if it doesn't exist
    create_products_availability_table()

async def broadcast_articles_periodically():
    """
    Broadcast articles periodically to connected WebSocket clients.
    """
    # Reduce broadcast frequency from 30s to 60s to lower CPU usage
    BROADCAST_INTERVAL = int(os.getenv('BROADCAST_INTERVAL_SECONDS', '60'))
    
    while True:
        try:
            with get_connection_from_pool() as conn:
                cursor = conn.cursor()
                
                query = get_optimized_query()
                cursor.execute(query)
                rows = cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                results = [dict(zip(columns, row)) for row in rows]
                
                # Serialize the data to JSON
                json_content = json.dumps(results, default=str)
                
                # Broadcast the data to all connected clients
                await manager.broadcast(json_content)
                
                # Log the broadcast
                print(f"Broadcasted articles data at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Don't need to close cursor here as it's handled by the context manager
        except Exception as e:
            print(f"Error broadcasting articles data: {e}")
        
        # Wait for the specified interval before the next update
        await asyncio.sleep(BROADCAST_INTERVAL)

def create_products_availability_table():
    """
    Create the products_availability table if it doesn't exist
    """
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            # Check if the table exists
            cursor.execute('''
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'products_availability'
            ''')
            
            table_exists = cursor.fetchone()[0] > 0
            
            if not table_exists:
                print("Creating products_availability table...")
                # Create the table
                cursor.execute('''
                    CREATE TABLE products_availability (
                        posizione INTEGER PRIMARY KEY,
                        codice VARCHAR(255) NOT NULL,
                        descrizione VARCHAR(255) NOT NULL
                    )
                ''')
                
                # Insert sample data if needed
                sample_data = [
                    {"posizione":1,"codice":"0P9GA0FI","descrizione":"PP9735 SINGLE HINGE STAND"},
                    {"posizione":2,"codice":"0P9GA1FI","descrizione":"PP9735W SINGLE HINGE STAND"},
                    {"posizione":3,"codice":"0P9EF6FI","descrizione":"PP9732W NO STAND"},
                    {"posizione":4,"codice":"0P9ET1FI","descrizione":"PP9715 DUAL HINGE STAND"},
                    {"posizione":5,"codice":"14886751","descrizione":"CORE I3 9100T FOR PP9715"},
                    {"posizione":6,"codice":"14886771","descrizione":"CORE I5 9500TE FOR PP9715"},
                    {"posizione":7,"codice":"0P9EG2FI","descrizione":"PP9745W SINGLE HINGE STAND"},
                    {"posizione":8,"codice":"0P9EQ3FI","descrizione":"XPOS PLUS 15,6 XP-3765W"},
                    {"posizione":9,"codice":"0P9EG1FI","descrizione":"PP9742W NO STAND"},
                    {"posizione":10,"codice":"14887030,14887031","descrizione":"CORE I3 12100 FOR PP9745W/9742W/XPOS PLUS 15,6"},
                    {"posizione":11,"codice":"14887020,14887021","descrizione":"CORE I5 12400 FOR PP9745W/9742W and XPOS PLUS 15,6"},
                    {"posizione":12,"codice":"0ST900SB","descrizione":"TP100 PRINTER USB-LAN-COM"},
                    {"posizione":13,"codice":"0MN858FI","descrizione":"MONITOR 15\" AM1015CL"},
                    {"posizione":14,"codice":"0MN860FI","descrizione":"MONITOR 22\" LD9022W"},
                    {"posizione":15,"codice":"0MN872FI","descrizione":"MONITOR 15\" AM1015CL"},
                    {"posizione":16,"codice":"0MN873FI","descrizione":"MONITOR 15\" XM-3015-AD"}
                ]
                
                insert_query = '''
                    INSERT INTO products_availability (posizione, codice, descrizione, is_hub)
                    VALUES (?, ?, ?, 1)
                '''

                for item in sample_data:
                    cursor.execute(insert_query, (item["posizione"], item["codice"], item["descrizione"]))
                    
                conn.commit()
                print("products_availability table created with sample data")
            else:
                print("products_availability table already exists")
            
    except Exception as e:
        print(f"Error creating products_availability table: {e}")

@app.get("/legami_details")
async def get_legami_details(article_code: str):
    """
    Get legami details for a specific article showing which parent articles contribute to the legami value.
    """
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()

            query = """
            select 
                mpl.mpl_padre,
                mpl.mpl_coimp,
                nvl((select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = mpl.mpl_padre and dep_code = 81),0) as parent_d81,
                mpl.mpl_coimp * nvl((select round(dep_qgiai+dep_qcar-dep_qsca,0) from mgdepo where dep_arti = mpl.mpl_padre and dep_code = 81),0) as contribution,
                (select amg_dest from mganag where amg_code = mpl.mpl_padre) as parent_description
            from mplegami mpl 
            where mpl.mpl_figlio = ?
            order by mpl.mpl_padre
            """

            cursor.execute(query, (article_code,))
            rows = cursor.fetchall()

            print(f"Legami details query for article {article_code}: found {len(rows)} rows")

            if not rows:
                print(f"No legami data found for article {article_code}")
                return JSONResponse(content={"details": [], "total": 0})

            # Convert the results to a list of dictionaries
            details = []
            total_contribution = 0
            
            for row in rows:
                parent_code = row[0]
                coefficient = float(row[1]) if row[1] is not None else 0.0
                parent_d81 = int(row[2]) if row[2] is not None else 0
                contribution = float(row[3]) if row[3] is not None else 0.0
                parent_desc = row[4] if row[4] is not None else ""
                
                details.append({
                    "parent_code": parent_code,
                    "parent_description": parent_desc,
                    "coefficient": coefficient,
                    "parent_d81": parent_d81,
                    "contribution": contribution
                })
                
                total_contribution += contribution

            result = {
                "details": details,
                "total": total_contribution
            }

            return JSONResponse(content=result)
        
    except Exception as e:
        print(f"Error getting legami details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting legami details: {str(e)}")

@app.get("/test_legami")
async def test_legami_table():
    """
    Test endpoint to check if mplegami table exists and has data.
    """
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()

            # First test if table exists and count rows
            test_query = "SELECT count(*) FROM mplegami"
            cursor.execute(test_query)
            count_result = cursor.fetchone()
            total_rows = count_result[0] if count_result else 0

            # Get first few rows as sample
            sample_query = "SELECT first 5 mpl_padre, mpl_figlio, mpl_coimp FROM mplegami"
            cursor.execute(sample_query)
            sample_rows = cursor.fetchall()

            # Test specifically for 0AC005MF
            test_specific_query = "SELECT mpl_padre, mpl_figlio, mpl_coimp FROM mplegami WHERE mpl_figlio = ?"
            cursor.execute(test_specific_query, ("0AC005MF",))
            specific_rows = cursor.fetchall()

            result = {
                "table_exists": True,
                "total_rows": total_rows,
                "sample_data": [
                    {
                        "padre": row[0],
                        "figlio": row[1], 
                        "coimp": float(row[2]) if row[2] is not None else 0.0
                    } for row in sample_rows
                ],
                "test_0AC005MF": [
                    {
                        "padre": row[0],
                        "figlio": row[1], 
                        "coimp": float(row[2]) if row[2] is not None else 0.0
                    } for row in specific_rows
                ]
            }

            return JSONResponse(content=result)
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error testing legami table: {error_msg}")
        return JSONResponse(content={
            "table_exists": False,
            "error": error_msg,
            "total_rows": 0,
            "sample_data": [],
            "test_0AC005MF": []
        })

@app.get("/today_orders")
async def get_today_orders():
    """
    Retrieves the orders of today
    """
    cursor = None  # Initialize cursor to None
    try:
        conn = get_cached_connection()
        cursor = conn.cursor()
        
        cursor.execute(today_orders_query)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
        
        return JSONResponse(content=jsonable_encoder(results))
        
    except Exception as e:
        print(f"Error fetching today's orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            cursor.close()

@app.get("/deposit_totals")
async def get_deposit_totals():
    """
    Retrieves the total deposit for each specified depot.
    """
    cursor = None  # Initialize cursor to None
    try:
        conn = get_cached_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT 
            dep_code,
            SUM(dep_qgiai + dep_qcar - dep_qsca + dep_qord + dep_qorp - dep_qpre - dep_qprp) AS total_deposit
        FROM 
            mgdepo
        GROUP BY 
            dep_code
        ORDER BY 
            dep_code;
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
        
        return JSONResponse(content=jsonable_encoder(results))
        
    except Exception as e:
        print(f"Error fetching deposit totals: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            cursor.close()


@app.get("/top_article")
async def get_top_article(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """
    Get the top performant article within a specified date range.
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
SELECT
    oc.occ_arti,
    (m.amg_desc || ' ' || m.amg_des2) AS article_description,
    mg.lne_desc AS categoria,
    SUM(oc.occ_qmov) AS total_occ_qmov,
    SUM(oc.occ_preu * oc.occ_qmov) AS total_soldi
FROM
    ocordic oc
JOIN
    ocordit ot ON oc.occ_tipo = ot.oct_tipo AND oc.occ_code = ot.oct_code
JOIN
    agagenti ag ON ot.oct_agen = ag.cod_agente
JOIN
    mganag m ON m.amg_code = oc.occ_arti
JOIN 
    mglinee mg ON m.amg_linp = mg.lne_code
WHERE
    oc.occ_dtco BETWEEN ? AND ?
GROUP BY
    oc.occ_arti,
    mg.lne_desc,
    m.amg_desc,
    m.amg_des2
ORDER BY 
    total_occ_qmov DESC


        """
        
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()
        
        results = []
        
        for row in rows:
            results.append({
                "occ_arti": row.occ_arti,
                "article_description": row.article_description,
                "total_occ_qmov": row.total_occ_qmov,
                "categoria": row.categoria,
                "total_soldi": row.total_soldi
            })
        
        json_content = json.dumps(results, default=str)
        return Response(content=json_content, media_type="application/json")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    finally:
        if cursor:
            cursor.close()
        print(f"Total execution time: {time.time() - start_time} seconds")

@app.get("/agents_total_sales")
async def get_agents_total_sales(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """
    Get the total sold quantity by each agent within a specified date range.
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT
            ag.des_agente,
            SUM(oc.occ_qmov) AS total_occ_qmov
        FROM
            ocordic oc
        JOIN
            ocordit ot ON oc.occ_tipo = ot.oct_tipo AND oc.occ_code = ot.oct_code
        JOIN
            agagenti ag ON ot.oct_agen = ag.cod_agente
        WHERE
            oc.occ_dtco BETWEEN ? AND ?
        GROUP BY
            ag.des_agente
        ORDER BY 
            total_occ_qmov DESC
        """
        
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "des_agente": row.des_agente,
                "total_occ_qmov": row.total_occ_qmov
            })
        
        json_content = json.dumps(results, default=str)
        return Response(content=json_content, media_type="application/json")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    finally:
        if cursor:
            cursor.close()
        print(f"Total execution time: {time.time() - start_time} seconds")


@app.get("/agent_article_sales")
async def get_agent_article_sales(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """
    Track the total sold quantity for each article per agent within a specified date range.
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT
            ag.des_agente,
            oc.occ_arti,
            (m.amg_desc || ' ' || m.amg_des2) AS article_description,

            SUM(oc.occ_qmov) AS total_occ_qmov
        FROM
            ocordic oc
        JOIN
            ocordit ot ON oc.occ_tipo = ot.oct_tipo AND oc.occ_code = ot.oct_code
        JOIN
            agagenti ag ON ot.oct_agen = ag.cod_agente
        JOIN
            mganag m ON m.amg_code = oc.occ_arti
        WHERE
            oc.occ_dtco BETWEEN ? AND ?
        GROUP BY
            ag.des_agente,
            oc.occ_arti,
                m.amg_desc,
    m.amg_des2
        ORDER BY 
            ag.des_agente,
            total_occ_qmov DESC
        """
        
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "des_agente": row.des_agente,
                "occ_arti": row.occ_arti,
                "article_description": row.article_description,
                "total_occ_qmov": row.total_occ_qmov
            })
        
        json_content = json.dumps(results, default=str)
        return Response(content=json_content, media_type="application/json")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    finally:
        if cursor:
            cursor.close()
        print(f"Total execution time: {time.time() - start_time} seconds")


@app.get("/fatturato_clienti")
async def get_agent_article_sales(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """
/* Fatturato per cliente */
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
    select  des_clifor, SUM(oct_impn) as total_soldi from ocordit JOIN
            agclifor ag ON oct_cocl = ag.cod_clifor
              WHERE
    oct_data BETWEEN ? AND ? group by des_clifor order by total_soldi desc
    
        """
        
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "des_clifor": row.des_clifor,
                "total_soldi": row.total_soldi
            })
        
        json_content = json.dumps(results, default=str)
        return Response(content=json_content, media_type="application/json")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    finally:
        if cursor:
            cursor.close()
        print(f"Total execution time: {time.time() - start_time} seconds")


@app.get("/fatturato_totale")
async def get_agent_article_sales(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """
/* Fatturato totale */
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
select  SUM(oct_impn) as total_soldi from ocordit  JOIN
            agagenti ag ON oct_agen = ag.cod_agente WHERE
    oct_data BETWEEN ? AND ?
    
    
        """
        
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "total_soldi": row.total_soldi
            })
        
        json_content = json.dumps(results, default=str)
        return Response(content=json_content, media_type="application/json")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    finally:
        if cursor:
            cursor.close()
        print(f"Total execution time: {time.time() - start_time} seconds")

@app.get("/fatturato_per_agente")
async def get_agent_article_sales(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """
/* Fatturato per agente */
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
select  ag.des_agente, SUM(oct_impn) as total_soldi from ocordit  JOIN
            agagenti ag ON oct_agen = ag.cod_agente WHERE
    oct_data BETWEEN ? AND ? group by des_agente
    
    
    
        """
        
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "des_agente": row.des_agente,

                "total_soldi": row.total_soldi
            })
        
        json_content = json.dumps(results, default=str)
        return Response(content=json_content, media_type="application/json")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    finally:
        if cursor:
            cursor.close()
        print(f"Total execution time: {time.time() - start_time} seconds")

@app.get("/fatturato_per_mese")
async def get_agent_article_sales(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """
/* Fatturato per mese */
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
SELECT 
    YEAR(oct_data) AS year,
    MONTH(oct_data) AS month,
    SUM(oct_impn) AS total_soldi
FROM 
    ocordit 
WHERE 
    oct_data BETWEEN ? and ?
GROUP BY 
    1,2
ORDER BY 
    year, month;
        """
        
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "year": row.year,
                "month": row.month,

                "total_soldi": row.total_soldi
            })
        
        json_content = json.dumps(results, default=str)
        return Response(content=json_content, media_type="application/json")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    finally:
        if cursor:
            cursor.close()
        print(f"Total execution time: {time.time() - start_time} seconds")



@app.get("/fatturato_per_giorno")
async def get_agent_article_sales(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """
/* Fatturato per giorno */
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """

SELECT 
    oct_data,
    SUM(oct_impn) AS total_soldi
FROM 
    ocordit 
WHERE 
    oct_data BETWEEN ? and ?
GROUP BY 
    oct_data
ORDER BY 
      oct_data
        """
        
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "oct_data": row.oct_data,
               

                "total_soldi": row.total_soldi
            })
        
        json_content = json.dumps(results, default=str)
        return Response(content=json_content, media_type="application/json")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    finally:
        if cursor:
            cursor.close()
        print(f"Total execution time: {time.time() - start_time} seconds")





@app.get("/suppliers")
async def suppliers(
    
):
    """
/* Fornitori */
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
select * from agclifor where cli_for = "F"

        """
        
        cursor.execute(query, )
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "cod_clifor": row.cod_clifor,
            

                "des_clifor": row.des_clifor
            })
        
        json_content = json.dumps(results, default=str)
        return Response(content=json_content, media_type="application/json")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    finally:
        if cursor:
            cursor.close()
        print(f"Total execution time: {time.time() - start_time} seconds")




@app.get("/supplier-orders")
async def supplier_orders(
    codice: str = Query(..., description="Start date in YYYY-MM-DD format"),
    
):
    """
/* Ordini fortniore*/
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
select * from ofordit where oft_cofo = ? order by oft_data desc


        """
        
        cursor.execute(query, (codice))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "oft_data": row.oft_data
            })
        
        json_content = json.dumps(results, default=str)
        return Response(content=json_content, media_type="application/json")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    finally:
        if cursor:
            cursor.close()
        print(f"Total execution time: {time.time() - start_time} seconds")





@app.get("/customer-orders")
async def customer_orders(
    codice: str = Query(..., description="Start date in YYYY-MM-DD format"),
    
):
    """
/* Ordini clienti passati*/
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
select mpf_arti, f.amg_desc mpf_desc, f.amg_grum, gf.gmg_desc, mpf_feva,
       mpf_qfab * gol_qord / mol_quaor totale, 
       (mpf_qfab-mpf_qpre)* gol_qord / mol_quaor residuo, 
       mol_parte, p.amg_desc mol_desc, 
       occ_tipo, occ_code, occ_riga, oct_data, oct_cocl, des_clifor,
       oct_stat
from mpfabbi, mpordil, mpordgol, ocordic, ocordit, agclifor, mganag f, mganag p, mggrum gf
where mpf_ordl = mol_code
and mol_code = gol_mpco
and gol_octi = occ_tipo and gol_occo = occ_code and gol_ocri = occ_riga
and oct_tipo = occ_tipo and oct_code = occ_code
and oct_cocl = cod_clifor
and mpf_arti = f.amg_code and f.amg_grum = gf.gmg_code
and mol_parte = p.amg_code
and mpf_arti = ?
and oct_data > (today - 120)
and oct_data <= today
union all
select occ_arti, f.amg_desc mpf_desc, f.amg_grum, gf.gmg_desc, occ_feva,
       occ_qmov, occ_qmov-occ_qcon residuo, 
       '' mol_parte, '' mol_desc, 
       occ_tipo, occ_code, occ_riga, oct_data, oct_cocl, des_clifor,
       oct_stat
from ocordic, ocordit, agclifor, mganag f, mggrum gf
where oct_tipo = occ_tipo and oct_code = occ_code
and oct_cocl = cod_clifor
and occ_arti = f.amg_code and f.amg_grum = gf.gmg_code
and occ_arti = ?
and oct_data > (today - 120)
and oct_data <= today
union all
select mpf_arti, f.amg_desc mpf_desc, f.amg_grum, gf.gmg_desc, mpf_feva,
       mpf_qfab, (mpf_qfab-mpf_qpre) residuo, 
       mol_parte, p.amg_desc mol_desc, 
       "OQ", 0, 0, mpf_dfab, 'ND', 'ORDINE QUADRO',
       '' as oct_stat
from mpfabbi, mpordil, mganag f, mganag p, mggrum gf
where mpf_ordl = mol_code
and mpf_arti = f.amg_code and f.amg_grum = gf.gmg_code
and mol_parte = p.amg_code
and mpf_ordl = 1
and mpf_arti = ?
ORDER BY oct_data desc


        """
        
        cursor.execute(query, (codice, codice, codice))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "occ_tipo": row.occ_tipo,
                "occ_code": row.occ_code,
                "oct_data": row.oct_data,
                "mpf_feva": row.mpf_feva,
                "totale": row.totale,
                "residuo": row.residuo,
                "oct_cocl": row.oct_cocl,
                "des_clifor": row.des_clifor
            })
        
        json_content = json.dumps(results, default=str)
        return Response(content=json_content, media_type="application/json")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if cursor:
            cursor.close()
        print(f"Total execution time: {time.time() - start_time} seconds")






@app.get("/fatturato_per_anno")
async def get_agent_article_sales(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """
/* Fatturato per mese */
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
SELECT 
    YEAR(oct_data) AS year,
    SUM(oct_impn) AS total_soldi
FROM 
    ocordit 
WHERE 
    oct_data BETWEEN ? and ?
GROUP BY 
    1
ORDER BY 
    year;

        """
        
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "year": row.year,
            

                "total_soldi": row.total_soldi
            })
        
        json_content = json.dumps(results, default=str)
        return Response(content=json_content, media_type="application/json")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    finally:
        if cursor:
            cursor.close()
        print(f"Total execution time: {time.time() - start_time} seconds")







@app.get("/article_disponibilita")
async def get_article_disponibilita(article_code: str):
    """
    Retrieves the availability data for a specific article code.
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



@app.get("/get_disponibilita_articoli")
async def get_article_disponibilita():
    """
    Retrieves the availability data for a specific article code.
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


@app.get("/get_disponibilita_articoli_commerciali")
async def get_disponibilita_articoli_commericali():
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

@app.post("/simulate_order")
async def simulate_order(request: Request):
    """
    Simulates an order to check component availability.
    Receives a list of article codes and quantities, and a time period, then returns availability data for all components.
    Time periods: 
    - "today": Current availability only
    - "mc": Current month (including demands and supplies for current month)
    - "ms": Next month (including demands and supplies for next month)
    - "msa": Two months ahead
    - "mss": Beyond two months
    """
    start_time = time.time()
    cursor = None
    try:
        # Parse the request body
        data = await request.json()
        items = data.get("items", [])
        time_period = data.get("time_period", "today")
        
        # Validate time_period
        valid_periods = ["today", "mc", "ms", "msa", "mss"]
        if time_period not in valid_periods:
            time_period = "today"  # Default to today if invalid
        
        if not items:
            return JSONResponse(
                content={"message": "No items provided for simulation."},
                status_code=400
            )
            
        conn = get_cached_connection()
        cursor = conn.cursor()
        
        # Lists to store all component article codes and their required quantities
        all_components = []
        component_quantities = {}
        component_parents = {}  # To track parent codes for each component
        
        # For each item in the request, get all its components
        for item in items:
            article_code = item.get("code")
            try:
                # Convert to integer immediately
                requested_quantity = int(float(item.get("quantity", 0)))
            except (ValueError, TypeError):
                requested_quantity = 0
            
            if not article_code or requested_quantity <= 0:
                continue
                
            # Query to get the components (bill of materials) for this article
            bom_query = """
            select m.mpl_padre, m.mpl_figlio, n.amg_dest, m.mpl_coimp
            from mplegami m
            inner join mganag n on (m.mpl_figlio = n.amg_code)
            where mpl_padre = ?
            """
            
            cursor.execute(bom_query, (article_code,))
            components = cursor.fetchall()
            
            # If no components found, add the article itself as a component
            if not components:
                # Get the article description
                article_query = "select amg_code, amg_dest from mganag where amg_code = ?"
                cursor.execute(article_query, (article_code,))
                article_row = cursor.fetchone()
                
                if article_row:
                    all_components.append({
                        "parent_code": None,
                        "code": article_row.amg_code,
                        "description": article_row.amg_dest,
                        "quantity_per_unit": 1,
                        "total_quantity": requested_quantity
                    })
                    
                    # Update the required quantity
                    component_quantities[article_row.amg_code] = component_quantities.get(article_row.amg_code, 0) + requested_quantity
                    # No parent to track since this is a standalone article
                    component_parents[article_row.amg_code] = ["None"]
            else:
                # Process each component
                for comp in components:
                    component_code = comp.mpl_figlio
                    parent_code = comp.mpl_padre
                    try:
                        # Convert to integer
                        quantity_per_unit = int(float(comp.mpl_coimp))
                    except (ValueError, TypeError):
                        quantity_per_unit = 1
                        
                    total_quantity = quantity_per_unit * requested_quantity
                    
                    all_components.append({
                        "parent_code": parent_code,
                        "code": component_code,
                        "description": comp.amg_dest,
                        "quantity_per_unit": quantity_per_unit,
                        "total_quantity": total_quantity
                    })
                    
                    # Update the required quantity
                    component_quantities[component_code] = component_quantities.get(component_code, 0) + total_quantity
                    
                    # Track parent for this component
                    if component_code not in component_parents:
                        component_parents[component_code] = []
                    if parent_code not in component_parents[component_code]:
                        component_parents[component_code].append(parent_code)
        
        # If no components were found for any items
        if not all_components:
            return JSONResponse(
                content={"message": "No components found for the provided items."},
                status_code=404
            )
            
        # Get unique component codes
        unique_component_codes = list(set(comp["code"] for comp in all_components))
        
        if not unique_component_codes:
            return JSONResponse(
                content={"message": "No valid component codes found."},
                status_code=404
            )
        
        # Use a single optimized query to get availability data for all components at once
        # Create the OR condition part of the query
        code_conditions = " OR ".join([f"amg_code = '{code}'" for code in unique_component_codes])
        
        availability_query = f"""
        select amg_code c_articolo, amg_dest d_articolo, amp_lead lt,
nvl((select round(dep_scom) from mgdepo where dep_arti = amg_code and dep_code = 1),0) scrt,
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
nvl((select sum(occ_qmov) from ocordic, ocordit where occ_arti = amg_code
  and occ_tipo = oct_tipo and occ_code = oct_code
  and oct_data between last_day(add_months(today,-3))+1 and last_day(add_months(today,-2))),0) +
nvl((select sum(mpf_qfab) from mpfabbi, mpordil where mpf_arti = amg_code 
  and mpf_ordl = mol_code and mol_code not in (select gol_mpco from mpordgol)
  and mol_dati between last_day(add_months(today,-3))+1 and last_day(add_months(today,-2))),0) + 
nvl((select sum(mpf_qfab) from mpfabbi, mpordil, mpordgol, ocordit where mpf_arti = amg_code 
  and mpf_ordl = mol_code and mol_code = gol_mpco and gol_octi = oct_tipo and gol_occo = oct_code
  and oct_data between last_day(add_months(today,-3))+1 and last_day(add_months(today,-2))),0) ord_mpp,
nvl((select sum(occ_qmov) from ocordic, ocordit where occ_arti = amg_code
  and occ_tipo = oct_tipo and occ_code = oct_code
  and oct_data between last_day(add_months(today,-2))+1 and last_day(add_months(today,-1))),0) +
nvl((select sum(mpf_qfab) from mpfabbi, mpordil where mpf_arti = amg_code 
  and mpf_ordl = mol_code and mol_code not in (select gol_mpco from mpordgol)
  and mol_dati between last_day(add_months(today,-2))+1 and last_day(add_months(today,-1))),0) + 
nvl((select sum(mpf_qfab) from mpfabbi, mpordil, mpordgol, ocordit where mpf_arti = amg_code 
  and mpf_ordl = mol_code and mol_code = gol_mpco and gol_octi = oct_tipo and gol_occo = oct_code
  and oct_data between last_day(add_months(today,-2))+1 and last_day(add_months(today,-1))),0) ord_mp,
nvl((select sum(occ_qmov) from ocordic, ocordit where occ_arti = amg_code
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
nvl((select sum(occ_qmov-occ_qcon) from ocordic, ocordit where occ_arti = amg_code and oct_stat != 'O' and occ_tipo = oct_tipo and occ_code = oct_code
and occ_feva = 'N'
  and occ_dtco between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))),0) +
nvl((select sum(mpf_qfab-mpf_qpre) from mpfabbi where mpf_arti = amg_code and mpf_feva = 'N'
  and mpf_dfab between last_day(add_months(today,0))+1 and last_day(add_months(today,+1))),0) dom_ms,
nvl((select sum(occ_qmov-occ_qcon) from ocordic, ocordit where occ_arti = amg_code and oct_stat != 'O' and occ_tipo = oct_tipo and occ_code = oct_code
and occ_feva = 'N'
  and occ_dtco between last_day(add_months(today,+1))+1 and last_day(add_months(today,+2))),0) +
nvl((select sum(mpf_qfab-mpf_qpre) from mpfabbi where mpf_arti = amg_code and mpf_feva = 'N'
  and mpf_dfab between last_day(add_months(today,+1))+1 and last_day(add_months(today,+2))),0) dom_msa,
nvl((select sum(occ_qmov-occ_qcon) from ocordic, ocordit where occ_arti = amg_code and oct_stat != 'O' and occ_tipo = oct_tipo and occ_code = oct_code
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
        avail_rows = cursor.fetchall()
        
        if not avail_rows:
            return JSONResponse(
                content={"message": "No availability data found for the components."},
                status_code=404
            )
        
        # Get column names and convert to list of dictionaries
        avail_columns = [column[0] for column in cursor.description]
        avail_data_list = [dict(zip(avail_columns, row)) for row in avail_rows]
        
        # Create a lookup dictionary for quick access to availability data by article code
        avail_data_by_code = {item["c_articolo"]: item for item in avail_data_list}
        
        # Helper function to calculate availability based on time period
        def calculate_availability(data, period):
            if not data:
                return 0
                
            try:
                # Current stock
                giac_d01 = int(data.get("giac_d01", 0))
                
                if period == "today":
                    return giac_d01
                    
                # Current month
                dom_mc = int(data.get("dom_mc", 0))
                off_mc = int(data.get("off_mc", 0))
                mc_result = giac_d01 - dom_mc + off_mc
                
                if period == "mc":
                    return mc_result
                    
                # Next month
                dom_ms = int(data.get("dom_ms", 0))
                off_ms = int(data.get("off_ms", 0))
                ms_result = mc_result - dom_ms + off_ms
                
                if period == "ms":
                    return ms_result
                    
                # Two months ahead
                dom_msa = int(data.get("dom_msa", 0))
                off_msa = int(data.get("off_msa", 0))
                msa_result = ms_result - dom_msa + off_msa
                
                if period == "msa":
                    return msa_result
                    
                # Beyond two months
                dom_mss = int(data.get("dom_mss", 0))
                off_mss = int(data.get("off_mss", 0))
                mss_result = msa_result - dom_mss + off_mss
                
                return mss_result
            except (ValueError, TypeError) as e:
                print(f"Error calculating availability: {e}")
                return 0
        
        # Build the final result with calculated availabilities
        availability_results = []
        
        for component_code in unique_component_codes:
            if component_code in avail_data_by_code:
                avail_data = avail_data_by_code[component_code]
                
                # Calculate current availability based on time period
                current_availability = calculate_availability(avail_data, time_period)
                
                # Calculate availability after simulation
                required_quantity = int(component_quantities.get(component_code, 0))
                simulated_availability = current_availability - required_quantity
                
                # Convert safety stock to integer
                try:
                    safety_stock = int(avail_data.get("scrt", 0))
                except (ValueError, TypeError):
                    safety_stock = 0
                
                # Convert lead time to integer
                try:
                    lead_time = int(avail_data.get("lt", 0))
                except (ValueError, TypeError):
                    lead_time = 0
                
                # Determine status
                status = "OK"
                if simulated_availability < 0:
                    status = "NOT_AVAILABLE"
                elif simulated_availability < safety_stock:
                    status = "PARTIAL"
                
                # Get parent codes for this component and join with commas
                parent_codes = component_parents.get(component_code, ["None"])
                parent_codes_str = ", ".join(parent_codes)
                
                # Add to results
                availability_results.append({
                    "code": component_code,
                    "description": avail_data.get("d_articolo", ""),
                    "parent_codes": parent_codes_str,
                    "requested_quantity": required_quantity,
                    "current_availability": current_availability,
                    "simulated_availability": simulated_availability,
                    "lead_time": lead_time,
                    "safety_stock": safety_stock,
                    "time_period": time_period,
                    "status": status
                })
            else:
                # If we couldn't find availability data, add a placeholder
                required_quantity = int(component_quantities.get(component_code, 0))
                
                # Look up the description if possible
                description = next((comp["description"] for comp in all_components if comp["code"] == component_code), "")
                
                # Get parent codes for this component and join with commas
                parent_codes = component_parents.get(component_code, ["None"])
                parent_codes_str = ", ".join(parent_codes)
                
                availability_results.append({
                    "code": component_code,
                    "description": description,
                    "parent_codes": parent_codes_str,
                    "requested_quantity": required_quantity,
                    "current_availability": 0,
                    "simulated_availability": -required_quantity,
                    "lead_time": 0,
                    "safety_stock": 0,
                    "time_period": time_period,
                    "status": "NOT_AVAILABLE"
                })
        
        # Sort results by status (NOT_AVAILABLE first, then PARTIAL, then OK)
        status_order = {"NOT_AVAILABLE": 0, "PARTIAL": 1, "OK": 2}
        availability_results.sort(key=lambda x: status_order.get(x["status"], 3))
        
        total_time = time.time() - start_time
        print(f"Total simulation execution time: {total_time} seconds")
        
        return JSONResponse(content=jsonable_encoder(availability_results))
            
    except Exception as e:
        print(f"Error during order simulation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        if cursor is not None:
            cursor.close()

def get_article_history_query():
    # SQL query with placeholders for the article code
    return """
select mpf_arti, f.amg_desc mpf_desc, f.amg_grum, gf.gmg_desc, 
       mpf_qfab * gol_qord / mol_quaor totale, 
       (mpf_qfab-mpf_qpre)* gol_qord / mol_quaor residuo, 
       mol_parte, p.amg_desc mol_desc, 
       occ_tipo, occ_code, occ_riga, occ_dtco, oct_cocl, des_clifor,
       oct_stat
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
       oct_stat
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
       '' as oct_stat
from mpfabbi, mpordil, mganag f, mganag p, mggrum gf
where mpf_ordl = mol_code
and mpf_arti = f.amg_code and f.amg_grum = gf.gmg_code
and mol_parte = p.amg_code
and mpf_feva = 'N'
and mpf_ordl = 1
and mpf_arti = ?
ORDER BY occ_dtco asc
    """

@app.get("/ordini_fornitore")
async def get_article_history(article_code: str):
    """
    Get article history for a specific article.
    """
    # Try to get results from cache first (cache for 10 minutes)
    
        
    start_time = time.time()
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()

            query = """
            select oft_tipo, oft_code, ofc_dtco as oft_data, ofc_qord, oft_cofo, des_clifor from ofordit 
 join  ofordic on ofc_tipo = oft_tipo and ofc_code = oft_code
 join agclifor on cod_clifor = oft_cofo
where ofc_arti = ? and oft_stat = "A"
"""

            # Execute the query with the article code parameter
            # Since the article code is used three times due to UNION ALL, we need to provide it three times
            params = (article_code)
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

            # Encode the results
            encoded_results = jsonable_encoder(results)
            
            # Cache the results

            total_time = time.time() - start_time
            print(f"Total execution time: {total_time} seconds")

            # Return the results as JSON
            return JSONResponse(content=encoded_results)

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/report_groups")
async def get_report_groups():
    """
    Retrieves all unique report group names from the report_groups table.
    
    Returns:
        A list of dictionaries, each containing a 'name' field with the unique group name.
    """
    start_time = time.time()
    cursor = None
    groups = []
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            # Query to get distinct group names
            query = "SELECT DISTINCT name FROM report_groups ORDER BY name"
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Only populate groups if we have results
            if results:
                # Format the results
                groups = [{"name": row[0]} for row in results]
            
            total_time = time.time() - start_time
            print(f"Total execution time for getting report groups: {total_time} seconds")
        
        return groups
        
    except Exception as e:
        print(f"Error getting report groups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception as e:
                print(f"Error closing cursor: {str(e)}")

@app.get("/report_groups/{name}/articles")
async def get_report_group_articles(name: str):
    """
    Retrieves all article codes for a specific report group.
    
    Args:
        name: The name of the report group to retrieve articles for.
        
    Returns:
        A list of article codes as strings.
    """
    start_time = time.time()
    cursor = None
    article_codes = []
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            # Query to get article codes for the specified group
            query = "SELECT art_code FROM report_groups WHERE name = ? ORDER BY art_code"
            cursor.execute(query, (name,))
            results = cursor.fetchall()
            
            # Only extract articles if results exist
            if results:
                # Extract the article codes
                article_codes = [row[0] for row in results]
            
            total_time = time.time() - start_time
            print(f"Total execution time for getting articles in group {name}: {total_time} seconds")
        
        return article_codes
        
    except Exception as e:
        print(f"Error getting articles for group {name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception as e:
                print(f"Error closing cursor: {str(e)}")

class ReportGroupItem(BaseModel):
    name: str
    art_code: str

@app.post("/report_groups")
async def add_to_report_group(item: ReportGroupItem):
    """
    Adds an article to a report group. If the group doesn't exist, it creates a new group.
    
    Args:
        item: A ReportGroupItem containing the group name and article code.
        
    Returns:
        A message indicating the success of the operation.
    """
    cursor = None
    message = ""
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            # Check if the entry already exists
            check_query = "SELECT COUNT(*) FROM report_groups WHERE name = ? AND art_code = ?"
            cursor.execute(check_query, (item.name, item.art_code))
            count = cursor.fetchone()[0]
            
            if count > 0:
                message = {"message": f"Article {item.art_code} is already in group {item.name}"}
            else:
                # Insert the new entry
                insert_query = "INSERT INTO report_groups (name, art_code) VALUES (?, ?)"
                cursor.execute(insert_query, (item.name, item.art_code))
                conn.commit()
                
                message = {"message": f"Article {item.art_code} added to group {item.name}"}
        
        return message
        
    except Exception as e:
        print(f"Error adding article to group: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception as e:
                print(f"Error closing cursor: {str(e)}")

@app.delete("/report_groups")
async def delete_from_report_group(
    name: str, 
    art_code: Optional[str] = None
):
    """
    Removes an article from a report group, or deletes an entire group if no article code is provided.
    
    Args:
        name: The name of the report group.
        art_code: (Optional) The article code to remove. If not provided, the entire group is deleted.
        
    Returns:
        A message indicating the success of the operation.
    """
    cursor = None
    message = ""
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            if art_code:
                # Delete a specific article from the group
                delete_query = "DELETE FROM report_groups WHERE name = ? AND art_code = ?"
                cursor.execute(delete_query, (name, art_code))
                conn.commit()
                
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail=f"Article {art_code} not found in group {name}")
                    
                message = {"message": f"Article {art_code} removed from group {name}"}
            else:
                # Delete the entire group
                delete_query = "DELETE FROM report_groups WHERE name = ?"
                cursor.execute(delete_query, (name,))
                conn.commit()
                
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail=f"Group {name} not found")
                    
                message = {"message": f"Group {name} deleted"}
        
        return message
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting from report group: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception as e:
                print(f"Error closing cursor: {str(e)}") 

@app.get("/report_groups/{name}/expanded_articles")
async def get_expanded_group_articles(name: str):
    """
    Retrieves all article codes for a specific report group and expands parent articles
    into their component articles using the mplegami table.
    
    Args:
        name: The name of the report group to retrieve articles for.
        
    Returns:
        A list of expanded article codes.
    """
    start_time = time.time()
    cursor = None
    expanded_article_codes = []
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            # First, get the original article codes for the group
            query = "SELECT art_code FROM report_groups WHERE name = ? ORDER BY art_code"
            cursor.execute(query, (name,))
            results = cursor.fetchall()
            
            if not results:
                total_time = time.time() - start_time
                print(f"Total execution time for getting expanded articles in group {name}: {total_time} seconds")
                return []
            
            # Extract the original article codes
            original_codes = [row[0] for row in results]
            
            # For each original code, check if it has components in mplegami
            for code in original_codes:
                # Check if this article is a parent (has components)
                component_query = "SELECT mpl_figlio FROM mplegami WHERE mpl_padre = ?"
                cursor.execute(component_query, (code,))
                component_results = cursor.fetchall()
                
                if component_results:
                    # This article has components, so add the component codes
                    component_codes = [row[0] for row in component_results]
                    expanded_article_codes.extend(component_codes)
                    print(f"Article {code} expanded to components: {component_codes}")
                else:
                    # This article has no components, so add the original code
                    expanded_article_codes.append(code)
                    print(f"Article {code} has no components, keeping original")
            
            # Remove duplicates while preserving order
            seen = set()
            unique_expanded_codes = []
            for code in expanded_article_codes:
                if code not in seen:
                    seen.add(code)
                    unique_expanded_codes.append(code.strip())
            total_time = time.time() - start_time
            print(f"Total execution time for getting expanded articles in group {name}: {total_time} seconds")
            print(f"Original codes: {original_codes}")
            print(f"Expanded codes: {unique_expanded_codes}")
        
        return unique_expanded_codes
        
    except Exception as e:
        print(f"Error getting expanded articles for group {name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception as e:
                print(f"Error closing cursor: {str(e)}")

@app.get("/price_list")
async def get_price_list():
    """
    Get price list data for all articles with price history and percentage changes
    """
    try:
        with get_connection_from_pool() as conn:
            cursor = conn.cursor()
            
            # Get all price data for all articles
            query = """
            SELECT
                c.ofc_arti,
                trim(c.ofc_desc)||' '||trim(nvl(c.ofc_des2,' ')) as descrizione,
                t.oft_data AS date,
                c.ofc_preu AS price,
                c.ofc_qord AS quantity,
                t.oft_valu AS valuta
            FROM
                ofordic c
                INNER JOIN ofordit t ON c.ofc_code = t.oft_code
            WHERE
                c.ofc_tipo != 'O'
                AND c.ofc_preu > 0
                AND c.ofc_arti is not null
            ORDER BY
                c.ofc_arti, t.oft_data ASC
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Process the data to get price history for each article
            articles_data = {}
            current_year = datetime.now().year
            
            for row in rows:
                article_code = row[0]
                description = row[1] if row[1] is not None else ''
                date = row[2]
                price = float(row[3]) if row[3] is not None else 0
                quantity = int(row[4]) if row[4] is not None else 0
                valuta = row[5] if row[5] is not None else 'EUR'
                
                # Skip rows with invalid data
                if article_code is None or date is None or price <= 0:
                    continue
                
                if article_code not in articles_data:
                    articles_data[article_code] = {
                        'prices': [],
                        'valuta': valuta,
                        'description': description
                    }
                
                articles_data[article_code]['prices'].append({
                    'date': date.strftime('%Y-%m-%d'),
                    'price': price,
                    'quantity': quantity
                })
            
            # Calculate price history for each article
            result = []
            for article_code, data in articles_data.items():
                prices = data['prices']
                if len(prices) == 0:
                    continue
                
                # Sort prices by date
                prices.sort(key=lambda x: x['date'])
                
                # Get first price
                first_price = prices[0]
                
                # Get last price (most recent)
                last_price = prices[-1]
                
                # Get last year's last price
                last_year_prices = [p for p in prices if p['date'].startswith(str(current_year - 1))]
                last_year_last_price = last_year_prices[-1] if last_year_prices else last_price
                
                # Get second last price (if exists)
                second_last_price = prices[-2] if len(prices) > 1 else last_price
                
                # Calculate percentage changes
                def calculate_percentage_change(old_price, new_price):
                    if old_price == 0:
                        return 0
                    return round(((new_price - old_price) / old_price) * 100, 2)
                
                # Calculate changes compared to last price
                first_to_last_change = calculate_percentage_change(first_price['price'], last_price['price'])
                last_year_to_last_change = calculate_percentage_change(last_year_last_price['price'], last_price['price'])
                second_last_to_last_change = calculate_percentage_change(second_last_price['price'], last_price['price'])
                
                result.append({
                    'article_code': article_code,
                    'description': data['description'],
                    'valuta': data['valuta'],
                    'first_price': {
                        'date': first_price['date'],
                        'price': first_price['price'],
                        'quantity': first_price['quantity']
                    },
                    'last_year_last_price': {
                        'date': last_year_last_price['date'],
                        'price': last_year_last_price['price'],
                        'quantity': last_year_last_price['quantity']
                    },
                    'second_last_price': {
                        'date': second_last_price['date'],
                        'price': second_last_price['price'],
                        'quantity': second_last_price['quantity']
                    },
                    'last_price': {
                        'date': last_price['date'],
                        'price': last_price['price'],
                        'quantity': last_price['quantity']
                    },
                    'changes': {
                        'first_to_last': first_to_last_change,
                        'last_year_to_last': last_year_to_last_change,
                        'second_last_to_last': second_last_to_last_change
                    }
                })
            
            # Sort by article code
            result.sort(key=lambda x: x['article_code'])
            
            return {
                'success': True,
                'data': result,
                'total_count': len(result)
            }
            
    except Exception as e:
        print(f"Error in get_price_list: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': f'Database error: {str(e)}'}
        )