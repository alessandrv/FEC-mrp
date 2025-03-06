from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import time
import pyodbc
import os

router = APIRouter()

# Database connection
def get_connection():
    try:
        conn = pyodbc.connect(
            f'DSN=fec;UID=informix;PWD=informix;'
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise


# Get all products
@router.get("/get_disponibilita_articoli")
async def get_article_disponibilita():
    """
    Retrieves all products from the availability table.
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Prepare the query
        query = '''SELECT * FROM products_availability ORDER BY posizione'''
        
        # Execute the query
        cursor.execute(query)
        
        # Fetch all results
        rows = cursor.fetchall()
        
        # Check if any rows were returned
        if not rows:
            return JSONResponse(
                content={"message": "No products found."},
                status_code=404
            )
        
        # Convert the results to a list of dictionaries
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
        
        total_time = time.time() - start_time
        print(f"Total execution time for get_disponibilita_articoli: {total_time} seconds")
        
        # Return the results as JSON
        return JSONResponse(content=jsonable_encoder(results))
        
    except Exception as e:
        print(f"Error getting products: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            cursor.close()

# Add a new product
@router.post("/add_disponibilita_articolo")
async def add_product_availability(request: Request):
    """
    Add a new product to the availability table
    """
    start_time = time.time()
    cursor = None
    try:
        # Get the request body
        body = await request.json()
        
        # Extract data from the request
        posizione = body.get('posizione')
        codice = body.get('codice')
        descrizione = body.get('descrizione')
        
        # Validate required fields
        if not all([posizione, codice, descrizione]):
            return JSONResponse(
                content={"message": "All fields (posizione, codice, descrizione) are required"},
                status_code=400
            )
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert the new record
        query = '''
            INSERT INTO products_availability 
            (posizione, codice, descrizione) 
            VALUES (?, ?, ?)
        '''
        
        cursor.execute(query, (posizione, codice, descrizione))
        conn.commit()
        
        total_time = time.time() - start_time
        print(f"Total execution time for add_disponibilita_articolo: {total_time} seconds")
        
        return JSONResponse(
            content={"message": "Product added successfully"},
            status_code=201
        )
        
    except Exception as e:
        print(f"Error adding product: {str(e)}")
        if "duplicate" in str(e).lower() or "primary key" in str(e).lower():
            return JSONResponse(
                content={"message": "Product with this position already exists"},
                status_code=409
            )
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            cursor.close()

# Update an existing product
@router.put("/update_disponibilita_articolo")
async def update_product_availability(request: Request):
    """
    Update an existing product in the availability table
    """
    start_time = time.time()
    cursor = None
    try:
        # Get the request body
        body = await request.json()
        
        # Extract data from the request
        posizione = body.get('posizione')
        codice = body.get('codice')
        descrizione = body.get('descrizione')
        
        # Validate required fields
        if not all([posizione, codice, descrizione]):
            return JSONResponse(
                content={"message": "All fields (posizione, codice, descrizione) are required"},
                status_code=400
            )
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if the record exists
        check_query = '''
            SELECT COUNT(*) FROM products_availability 
            WHERE posizione = ?
        '''
        
        cursor.execute(check_query, (posizione,))
        count = cursor.fetchone()[0]
        
        if count == 0:
            return JSONResponse(
                content={"message": "Product not found"},
                status_code=404
            )
        print("CIAO")
        # Update the record
        update_query = '''
            UPDATE products_availability 
            SET codice = ?, descrizione = ? 
            WHERE posizione = ?
        '''
        
        cursor.execute(update_query, (codice, descrizione, posizione))
        conn.commit()
        
        total_time = time.time() - start_time
        print(f"Total execution time for update_disponibilita_articolo: {total_time} seconds")
        
        return JSONResponse(
            content={"message": "Product updated successfully"},
            status_code=200
        )
        
    except Exception as e:
        print(f"Error updating product: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            cursor.close()

# Delete a product
@router.delete("/delete_disponibilita_articolo/{posizione}")
async def delete_product_availability(posizione: int):
    """
    Delete a product from the availability table
    """
    start_time = time.time()
    cursor = None
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if the record exists
        check_query = '''
            SELECT COUNT(*) FROM products_availability 
            WHERE posizione = ?
        '''
        
        cursor.execute(check_query, (posizione,))
        count = cursor.fetchone()[0]
        
        if count == 0:
            return JSONResponse(
                content={"message": "Product not found"},
                status_code=404
            )
        
        # Start a transaction
        conn.autocommit = False
        
        try:
            # Delete the record
            delete_query = '''
                DELETE FROM products_availability 
                WHERE posizione = ?
            '''
            
            cursor.execute(delete_query, (posizione,))
            
            # Renumber positions
            renumber_query = '''
                UPDATE products_availability 
                SET posizione = posizione - 1 
                WHERE posizione > ?
            '''
            
            cursor.execute(renumber_query, (posizione,))
            
            # Commit the transaction
            conn.commit()
            
        except Exception as e:
            # Rollback in case of error
            conn.rollback()
            raise e
        finally:
            # Reset autocommit
            conn.autocommit = True
        
        total_time = time.time() - start_time
        print(f"Total execution time for delete_disponibilita_articolo: {total_time} seconds")
        
        return JSONResponse(
            content={"message": "Product deleted successfully"},
            status_code=200
        )
        
    except Exception as e:
        print(f"Error deleting product: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            cursor.close()

# Update the order of products
@router.put("/update_disponibilita_articoli_order")
async def update_product_availability_order(request: Request):
    """
    Update the order of products in the availability table by swapping the positions of two products.
    This version uses Informix syntax and swaps the keys by setting one of them to maxint temporarily.
    """
    import time
    start_time = time.time()
    cursor = None
    conn = None
    try:
        # Expect exactly two products to swap
        body = await request.json()
        if not isinstance(body, list):
            return JSONResponse(
                content={"message": "Request body must be an array of products"},
                status_code=400
            )
        if len(body) != 2:
            return JSONResponse(
                content={"message": "Request body must contain exactly 2 products"},
                status_code=400
            )
        
        # Retrieve the two positions to swap
        posA = body[0].get('posizione')
        posB = body[1].get('posizione')
        
        if posA is None or posB is None:
            return JSONResponse(
                content={"message": "Each product must have a 'posizione' field"},
                status_code=400
            )
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Start transaction
        conn.autocommit = False
        
        try:
            # Define maxint value (assuming the 'posizione' column is an INTEGER)
            maxint = 2147483647
            
            # Step 1: Temporarily set product A's key to maxint
            cursor.execute(
                "UPDATE products_availability SET posizione = ? WHERE posizione = ?",
                (maxint, posA)
            )
            
            # Step 2: Set product B's key to product A's original position
            cursor.execute(
                "UPDATE products_availability SET posizione = ? WHERE posizione = ?",
                (posA, posB)
            )
            
            # Step 3: Set the product with the temporary key (maxint) to product B's original position
            cursor.execute(
                "UPDATE products_availability SET posizione = ? WHERE posizione = ?",
                (posB, maxint)
            )
            
            # Commit the transaction
            conn.commit()
            
        except Exception as e:
            # Rollback in case of any error
            conn.rollback()
            raise e
        finally:
            # Reset autocommit mode
            conn.autocommit = True
        
        total_time = time.time() - start_time
        print(f"Total execution time for update_disponibilita_articoli_order: {total_time} seconds")
        
        return JSONResponse(
            content={"message": "Product order updated successfully"},
            status_code=200
        )
        
    except Exception as e:
        print(f"Error updating product order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            cursor.close()

    """
    Update the order of products in the availability table
    """
    start_time = time.time()
    cursor = None
    conn = None
    try:
        # Get the request body which should be an array of products with positions
        body = await request.json()
        
        if not isinstance(body, list):
            return JSONResponse(
                content={"message": "Request body must be an array of products"},
                status_code=400
            )
            
        if len(body) == 0:
            return JSONResponse(
                content={"message": "Request body cannot be empty"},
                status_code=400
            )
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Start a transaction
        conn.autocommit = False
        
        try:
            # Create a temporary table for the reordering
            cursor.execute('''
                IF OBJECT_ID('tempdb..#temp_positions') IS NOT NULL
                    DROP TABLE #temp_positions
                
                CREATE TABLE #temp_positions (
                    old_position INT,
                    new_position INT
                )
            ''')
            
            # Insert the new ordering into the temporary table
            for i, item in enumerate(body, 1):
                old_position = item.get('posizione')
                if not old_position:
                    raise ValueError("Each item must have a 'posizione' field")
                
                cursor.execute(
                    'INSERT INTO #temp_positions (old_position, new_position) VALUES (?, ?)',
                    (old_position, i)
                )
            
            # Create a temporary holding table for the actual records
            cursor.execute('''
                IF OBJECT_ID('tempdb..#temp_records') IS NOT NULL
                    DROP TABLE #temp_records
                
                SELECT 
                    p.posizione,
                    p.codice,
                    p.descrizione,
                    t.new_position
                INTO #temp_records
                FROM products_availability p
                JOIN #temp_positions t ON p.posizione = t.old_position
            ''')
            
            # Clear the original table
            cursor.execute('DELETE FROM products_availability')
            
            # Insert the records back with their new positions
            cursor.execute('''
                INSERT INTO products_availability (posizione, codice, descrizione)
                SELECT new_position, codice, descrizione
                FROM #temp_records
                ORDER BY new_position
            ''')
            
            # Drop temporary tables
            cursor.execute('''
                DROP TABLE #temp_positions
                DROP TABLE #temp_records
            ''')
            
            # Commit the transaction
            conn.commit()
            
        except Exception as e:
            # Rollback in case of error
            conn.rollback()
            raise e
        finally:
            # Reset autocommit
            conn.autocommit = True
        
        total_time = time.time() - start_time
        print(f"Total execution time for update_disponibilita_articoli_order: {total_time} seconds")
        
        return JSONResponse(
            content={"message": "Product order updated successfully"},
            status_code=200
        )
        
    except Exception as e:
        print(f"Error updating product order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            cursor.close()

# Get description for an article code
@router.get("/get_article_description/{code}")
async def get_article_description(code: str):
    """
    Retrieves the description for an article code from the mganag table
    """
    start_time = time.time()
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Prepare the query
        query = '''
            SELECT amg_desc, amg_des2 
            FROM mganag 
            WHERE amg_code = ?
        '''
        
        # Execute the query
        cursor.execute(query, (code,))
        
        # Fetch the result
        row = cursor.fetchone()
        
        # Check if any row was returned
        if not row:
            return JSONResponse(
                content={"message": f"No description found for code: {code}"},
                status_code=404
            )
        
        # Extract and concatenate the descriptions
        desc = row[0].strip() if row[0] else ""
        des2 = row[1].strip() if row[1] else ""
        full_description = f"{desc} {des2}".strip()
        
        total_time = time.time() - start_time
        print(f"Total execution time for get_article_description: {total_time} seconds")
        
        # Return the result as JSON
        return JSONResponse(
            content={"description": full_description},
            status_code=200
        )
        
    except Exception as e:
        print(f"Error getting article description: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            cursor.close() 