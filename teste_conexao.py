import mysql.connector

try:
    conn = mysql.connector.connect(
        host='trolley.proxy.rlwy.net',
        port=56440,
        user='root',
        password='tKiyKmLdCVkXiCbPHJmSRjWvZegSVtWY',
        database='railway',
        ssl_disabled=False
    )
    print('✅ Conectado!' if conn.is_connected() else '❌ Falhou')
    conn.close()
except Exception as e:
    print(f'❌ Erro: {e}')