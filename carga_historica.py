import csv, psycopg2, sys, os
from datetime import datetime

archivos = [
    '/tmp/Servicios__40_.csv',
    '/tmp/Servicios__41_.csv',
    '/tmp/Servicios__42_.csv',
    '/tmp/Servicios__43_.csv',
    '/tmp/Servicios__44_.csv',
]

conn = psycopg2.connect(
    host='172.16.1.1', port=5432,
    dbname='quickops_db', user='n8n_user', password='Quick2026!Ops'
)
cur = conn.cursor()

SQL = """
INSERT INTO smartquick_services
  (service_id, client, city, warehouse, service_type, driver, status,
   freight_value, pieces, created_at, payload)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (service_id) DO UPDATE SET
  status        = EXCLUDED.status,
  warehouse     = COALESCE(EXCLUDED.warehouse, smartquick_services.warehouse),
  driver        = COALESCE(EXCLUDED.driver, smartquick_services.driver),
  freight_value = EXCLUDED.freight_value,
  city          = COALESCE(EXCLUDED.city, smartquick_services.city),
  updated_db_at = now()
"""

total_ok = 0
batch = []
BATCH_SIZE = 500

def flush(batch):
    try:
        cur.executemany(SQL, batch)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f'\n  ERROR batch: {e}')

for archivo in archivos:
    if not os.path.exists(archivo):
        print(f'No encontrado: {archivo}')
        continue
    file_ok = 0
    with open(archivo, encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=';')
        headers = next(reader)
        for row in reader:
            if len(row) < 30:
                continue
            guia = row[11].strip()
            if not guia:
                continue
            # Fecha operativa col 20
            fecha_str = row[20].strip()
            fecha_dt = None
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'):
                try:
                    fecha_dt = datetime.strptime(fecha_str, fmt)
                    break
                except:
                    pass

            estado    = row[12].strip() or None
            cliente   = row[14].strip() or None
            cedi      = row[22].strip() or None
            ciudad    = row[27].strip() or None
            conductor = row[28].strip() or None
            tipo_svc  = row[29].strip() or None
            flete2    = row[58].strip() if len(row) > 58 else ''
            try:
                flete_val = float(flete2.replace(',','.')) if flete2 else 0.0
            except:
                flete_val = 0.0

            batch.append((
                guia, cliente, ciudad, cedi, tipo_svc, conductor,
                estado, flete_val, 1, fecha_dt, '{}'
            ))
            file_ok += 1
            total_ok += 1
            if len(batch) >= BATCH_SIZE:
                flush(batch)
                batch = []
                sys.stdout.write(f'\r  {total_ok:,} registros procesados...')
                sys.stdout.flush()

    print(f'\n{os.path.basename(archivo)}: {file_ok:,} registros ✓')

if batch:
    flush(batch)

cur.close()
conn.close()
print(f'\n✅ CARGA COMPLETA: {total_ok:,} registros insertados/actualizados')
