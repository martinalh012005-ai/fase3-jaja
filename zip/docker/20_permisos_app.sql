-- Se ejecuta DESPUÉS de script_integral.sql (orden alfabético en /docker-entrypoint-initdb.d).
-- El script integral recrea la base; aquí se deja al usuario de la aplicación con mínimo privilegio:
-- solo DML y ejecución de rutinas (sin DDL, sin DROP).
REVOKE ALL PRIVILEGES ON turismo_astronomico.* FROM 'astro_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON turismo_astronomico.* TO 'astro_app'@'%';
FLUSH PRIVILEGES;
