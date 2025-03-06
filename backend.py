import pyodbc
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, HTTPException, Query
import json
import time
from functools import lru_cache
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import List
import asyncio

app = FastAPI()

# Configure CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","https://fecpos.it", "http://172.16.16.66:3000", "http://172.16.16.66:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_connection():
    conn = pyodbc.connect(
       'DSN=fec;UID=informix;PWD=informix;'
    )
    return conn

def get_cached_connection():
    # Removed caching to avoid using stale connections
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
@app.get("/articles")
async def get_articles():
    start_time = time.time()
    cursor = None  # Initialize cursor to None
    try:
        conn = get_cached_connection()
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
        
        total_time = time.time() - start_time
        print(f"Total execution time: {total_time} seconds")
        
        return Response(
            content=json_content,
            media_type="application/json"
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        raise
    finally:
        if cursor is not None:
            cursor.close()

@app.get("/article_price")
async def get_article_price(article_code: str):
    start_time = time.time()
    cursor = None  # Initialize cursor to None
    try:
        conn = get_cached_connection()
        cursor = conn.cursor()
        
        # Prepare the query
        query = get_article_price_query()
        
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
        results = [
            dict(zip(columns, row))
            for row in rows
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
            'valuta': valuta,
            'maxPriceData': maxPriceData,
            'minPriceData': minPriceData,
        }
        
        total_time = time.time() - start_time
        print(f"Total execution time: {total_time} seconds")
        
        return JSONResponse(content=jsonable_encoder(response))
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise
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
async def get_article_history(article_code: str):
    start_time = time.time()
    cursor = None  # Initialize cursor to None
    try:
        conn = get_cached_connection()
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
    asyncio.create_task(broadcast_articles_periodically())
async def broadcast_articles_periodically():
    while True:
        cursor = None  # Initialize cursor to None
        try:
            # Fetch the latest articles data
            conn = get_cached_connection()
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
        except Exception as e:
            print(f"Error broadcasting articles data: {e}")
        finally:
            if cursor is not None:
                cursor.close()
        
        # Wait for a specified interval before the next update
        await asyncio.sleep(30)  # Broadcast every 30 seconds



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
        query = '''select * from products_availability'''
        
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








