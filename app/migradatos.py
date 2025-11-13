import sqlite3
from sqlalchemy import create_engine, MetaData, Table, insert
from sqlalchemy.exc import SQLAlchemyError

# === CONFIGURACIÓN ===

# Ruta a tu base SQLite local
sqlite_path = "app/obras.db"

# URL de tu base PostgreSQL en Render
postgres_url = "postgresql://bs_mariomendoza_user:XNBiVHbS8F7KwsYtHlkGUYTOgQ87h3dW@dpg-d4agomjipnbc739kf190-a.virginia-postgres.render.com/bs_mariomendoza"

# === CONEXIONES ===
sqlite_conn = sqlite3.connect(sqlite_path)
pg_engine = create_engine(postgres_url)
metadata = MetaData()

# Obtener tablas del SQLite
sqlite_cursor = sqlite_conn.cursor()
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tablas = [fila[0] for fila in sqlite_cursor.fetchall()]

print(f"🔹 Tablas encontradas en SQLite: {tablas}\n")

for tabla in tablas:
    try:
        # Leer datos de la tabla SQLite
        df = []
        columnas = [col[1] for col in sqlite_cursor.execute(f"PRAGMA table_info({tabla});")]
        query = f"SELECT * FROM {tabla}"
        filas = sqlite_cursor.execute(query).fetchall()
        print(f"➡️ Migrando tabla: {tabla} ({len(filas)} registros)")

        # Crear tabla en PostgreSQL si no existe
        sqlite_cursor.execute(f"PRAGMA table_info({tabla});")
        columnas_info = sqlite_cursor.fetchall()

        cols_def = []
        for col in columnas_info:
            nombre = col[1]
            tipo = col[2]
            if "INT" in tipo.upper():
                cols_def.append(f"{nombre} INTEGER")
            elif "CHAR" in tipo.upper() or "TEXT" in tipo.upper():
                cols_def.append(f"{nombre} TEXT")
            elif "REAL" in tipo.upper() or "FLOAT" in tipo.upper():
                cols_def.append(f"{nombre} FLOAT")
            else:
                cols_def.append(f"{nombre} TEXT")

        cols_sql = ", ".join(cols_def)
        create_stmt = f"CREATE TABLE IF NOT EXISTS {tabla} ({cols_sql});"

        with pg_engine.connect() as conn:
            conn.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE;")
            conn.execute(create_stmt)
            conn.commit()

            # Insertar datos
            if filas:
                placeholders = ", ".join([f":{c}" for c in columnas])
                insert_stmt = f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({placeholders})"
                for fila in filas:
                    valores = dict(zip(columnas, fila))
                    conn.execute(insert_stmt, valores)
                conn.commit()

        print(f"✅ {len(filas)} registros migrados correctamente.\n")

    except SQLAlchemyError as e:
        print(f"❌ Error al migrar {tabla}: {e}")

sqlite_conn.close()
print("🎉 Migración completada exitosamente.")
