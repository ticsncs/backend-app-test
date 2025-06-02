import psycopg2

conn = psycopg2.connect(
    dbname="bd_backend_app",
    user="postgres",
    password="ServerNCS011",
    host="localhost",
    port="5432"
)
print("Conectado correctamente")
