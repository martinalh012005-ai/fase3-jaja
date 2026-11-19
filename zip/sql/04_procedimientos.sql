-- =====================================================================
-- 04_procedimientos.sql : 6 procedimientos almacenados (R1, R4, R9, R10, R11, R12)
-- Todos validan sus parámetros con SIGNAL y devuelven un único result set.
-- =====================================================================
USE turismo_astronomico;
DELIMITER $$

-- ---------------------------------------------------------------------
-- R1. Zonas de observación que reciben mayor cantidad de visitantes
--     mediante actividades en un período.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_r1_zonas_mas_visitadas$$
CREATE PROCEDURE sp_r1_zonas_mas_visitadas(IN p_inicio DATE, IN p_fin DATE)
BEGIN
    IF p_inicio IS NULL OR p_fin IS NULL OR p_inicio > p_fin THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Rango de fechas inválido: inicio debe ser <= término';
    END IF;

    SELECT  c.nombre                          AS centro,
            z.nombre                          AS zona,
            COUNT(DISTINCT a.id_actividad)    AS actividades,
            COUNT(r.id_reserva)               AS reservas_confirmadas,
            SUM(r.asistencia_efectiva)        AS visitantes_asistentes
    FROM    zona_observacion z
    JOIN    centro_astronomico c    ON c.id_centro    = z.id_centro
    JOIN    actividad_observacion a ON a.id_zona      = z.id_zona
    JOIN    reserva r               ON r.id_actividad = a.id_actividad
    WHERE   a.estado = 'REALIZADA'
      AND   r.estado = 'CONFIRMADA'
      AND   a.fecha BETWEEN p_inicio AND p_fin
    GROUP BY c.id_centro, c.nombre, z.id_zona, z.nombre
    ORDER BY visitantes_asistentes DESC, reservas_confirmadas DESC;
END$$

-- ---------------------------------------------------------------------
-- R4. Centros que concentran la mayor cantidad de actividades y
--     visitantes en un período.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_r4_centros_actividades_visitantes$$
CREATE PROCEDURE sp_r4_centros_actividades_visitantes(IN p_inicio DATE, IN p_fin DATE)
BEGIN
    IF p_inicio IS NULL OR p_fin IS NULL OR p_inicio > p_fin THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Rango de fechas inválido: inicio debe ser <= término';
    END IF;

    SELECT  c.nombre                                   AS centro,
            COUNT(DISTINCT a.id_actividad)             AS actividades_realizadas,
            COUNT(DISTINCT z.id_zona)                  AS zonas_utilizadas,
            COUNT(DISTINCT CASE WHEN r.asistencia_efectiva = 1 THEN r.id_visitante END)
                                                       AS visitantes_distintos,
            COALESCE(SUM(r.asistencia_efectiva), 0)    AS asistencias_totales
    FROM    centro_astronomico c
    JOIN    zona_observacion z      ON z.id_centro = c.id_centro
    JOIN    actividad_observacion a ON a.id_zona   = z.id_zona
    LEFT JOIN reserva r             ON r.id_actividad = a.id_actividad AND r.estado = 'CONFIRMADA'
    WHERE   a.estado = 'REALIZADA'
      AND   a.fecha BETWEEN p_inicio AND p_fin
    GROUP BY c.id_centro, c.nombre
    ORDER BY actividades_realizadas DESC, visitantes_distintos DESC;
END$$

-- ---------------------------------------------------------------------
-- R9. Actividades que superan el promedio de asistentes de las
--     actividades realizadas en el mismo centro durante un período.
--     (subconsulta correlacionada por centro)
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_r9_actividades_sobre_promedio_centro$$
CREATE PROCEDURE sp_r9_actividades_sobre_promedio_centro(
    IN p_centro INT UNSIGNED, IN p_inicio DATE, IN p_fin DATE)
BEGIN
    IF p_inicio IS NULL OR p_fin IS NULL OR p_inicio > p_fin THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Rango de fechas inválido: inicio debe ser <= término';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM centro_astronomico WHERE id_centro = p_centro) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El centro indicado no existe';
    END IF;

    WITH asist AS (
        SELECT  a.id_actividad, a.cod_actividad, a.nombre AS actividad, a.fecha,
                z.id_zona, z.nombre AS zona, c.id_centro, c.nombre AS centro,
                COALESCE(SUM(r.asistencia_efectiva), 0) AS asistentes
        FROM    actividad_observacion a
        JOIN    zona_observacion z   ON z.id_zona   = a.id_zona
        JOIN    centro_astronomico c ON c.id_centro = z.id_centro
        LEFT JOIN reserva r          ON r.id_actividad = a.id_actividad AND r.estado = 'CONFIRMADA'
        WHERE   a.estado = 'REALIZADA'
          AND   c.id_centro = p_centro
          AND   a.fecha BETWEEN p_inicio AND p_fin
        GROUP BY a.id_actividad, a.cod_actividad, a.nombre, a.fecha, z.id_zona, z.nombre, c.id_centro, c.nombre
    )
    SELECT  x.centro, x.zona, x.cod_actividad, x.actividad, x.fecha, x.asistentes,
            (SELECT ROUND(AVG(y.asistentes), 2) FROM asist y WHERE y.id_centro = x.id_centro)
                AS promedio_del_centro
    FROM    asist x
    WHERE   x.asistentes > (SELECT AVG(y.asistentes) FROM asist y WHERE y.id_centro = x.id_centro)
    ORDER BY x.asistentes DESC, x.fecha;
END$$

-- ---------------------------------------------------------------------
-- R10. Zonas con nivel de oscuridad superior al promedio de las zonas del
--      mismo centro y actividades que se realizan en ellas.
--      (subconsulta correlacionada por centro)
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_r10_zonas_oscuras_y_actividades$$
CREATE PROCEDURE sp_r10_zonas_oscuras_y_actividades(IN p_centro INT UNSIGNED)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM centro_astronomico WHERE id_centro = p_centro) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El centro indicado no existe';
    END IF;

    SELECT  c.nombre                    AS centro,
            z.nombre                    AS zona,
            z.nivel_oscuridad,
            (SELECT ROUND(AVG(z2.nivel_oscuridad), 2)
               FROM zona_observacion z2 WHERE z2.id_centro = z.id_centro) AS promedio_oscuridad_centro,
            a.cod_actividad,
            a.nombre                    AS actividad,
            a.modalidad,
            a.estado
    FROM    zona_observacion z
    JOIN    centro_astronomico c ON c.id_centro = z.id_centro
    LEFT JOIN actividad_observacion a ON a.id_zona = z.id_zona
    WHERE   c.id_centro = p_centro
      AND   z.nivel_oscuridad > (SELECT AVG(z2.nivel_oscuridad)
                                   FROM zona_observacion z2
                                  WHERE z2.id_centro = z.id_centro)
    ORDER BY z.nivel_oscuridad DESC, a.fecha;
END$$

-- ---------------------------------------------------------------------
-- R11. Visitantes que han participado en más actividades que el promedio
--      de los visitantes y cuya evaluación promedio supera el promedio
--      general. (subconsulta + agrupación)
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_r11_visitantes_destacados$$
CREATE PROCEDURE sp_r11_visitantes_destacados(IN p_inicio DATE, IN p_fin DATE)
BEGIN
    IF p_inicio IS NULL OR p_fin IS NULL OR p_inicio > p_fin THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Rango de fechas inválido: inicio debe ser <= término';
    END IF;

    SELECT  CONCAT(p.nombre_pila, ' ', p.ap_paterno) AS visitante,
            COUNT(r.id_reserva)                      AS actividades_asistidas,
            ROUND(AVG(e.calificacion), 2)            AS evaluacion_promedio,
            COUNT(e.id_evaluacion)                   AS evaluaciones_emitidas
    FROM    visitante v
    JOIN    persona p               ON p.id_persona   = v.id_persona
    JOIN    reserva r               ON r.id_visitante = v.id_persona
                                   AND r.estado = 'CONFIRMADA' AND r.asistencia_efectiva = 1
    JOIN    actividad_observacion a ON a.id_actividad = r.id_actividad
                                   AND a.fecha BETWEEN p_inicio AND p_fin
    JOIN    evaluacion e            ON e.id_reserva   = r.id_reserva
    GROUP BY v.id_persona, p.nombre_pila, p.ap_paterno
    HAVING  COUNT(r.id_reserva) > (
                SELECT AVG(q.n) FROM (
                    SELECT COUNT(*) AS n
                    FROM   reserva r2
                    JOIN   actividad_observacion a2 ON a2.id_actividad = r2.id_actividad
                    WHERE  r2.estado = 'CONFIRMADA' AND r2.asistencia_efectiva = 1
                      AND  a2.fecha BETWEEN p_inicio AND p_fin
                    GROUP BY r2.id_visitante) q)
       AND  AVG(e.calificacion) > (
                SELECT AVG(e3.calificacion)
                FROM   evaluacion e3
                JOIN   reserva r3 ON r3.id_reserva = e3.id_reserva
                JOIN   actividad_observacion a3 ON a3.id_actividad = r3.id_actividad
                WHERE  a3.fecha BETWEEN p_inicio AND p_fin)
    ORDER BY actividades_asistidas DESC, evaluacion_promedio DESC;
END$$

-- ---------------------------------------------------------------------
-- R12. Centros con promedio de asistentes por actividad superior al
--      promedio general de todos los centros en el período.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_r12_centros_sobre_promedio_general$$
CREATE PROCEDURE sp_r12_centros_sobre_promedio_general(IN p_inicio DATE, IN p_fin DATE)
BEGIN
    IF p_inicio IS NULL OR p_fin IS NULL OR p_inicio > p_fin THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Rango de fechas inválido: inicio debe ser <= término';
    END IF;

    WITH asist AS (
        SELECT  a.id_actividad, c.id_centro, c.nombre AS centro, z.id_zona,
                COALESCE(SUM(r.asistencia_efectiva), 0) AS asistentes
        FROM    actividad_observacion a
        JOIN    zona_observacion z   ON z.id_zona   = a.id_zona
        JOIN    centro_astronomico c ON c.id_centro = z.id_centro
        LEFT JOIN reserva r          ON r.id_actividad = a.id_actividad AND r.estado = 'CONFIRMADA'
        WHERE   a.estado = 'REALIZADA'
          AND   a.fecha BETWEEN p_inicio AND p_fin
        GROUP BY a.id_actividad, c.id_centro, c.nombre, z.id_zona
    )
    SELECT  centro,
            COUNT(*)                          AS actividades,
            ROUND(AVG(asistentes), 2)         AS promedio_asistentes_por_actividad,
            (SELECT ROUND(AVG(asistentes), 2) FROM asist) AS promedio_general
    FROM    asist
    GROUP BY id_centro, centro
    HAVING  AVG(asistentes) > (SELECT AVG(asistentes) FROM asist)
    ORDER BY promedio_asistentes_por_actividad DESC;
END$$

DELIMITER ;
