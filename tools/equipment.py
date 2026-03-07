"""설비 도구 (4개) — 설비별 불량, 비가동, 정비 이력, 파라미터 이상."""

from tools import query, to_json


def register(mcp):
    """mcp 인스턴스에 설비 도구 4개 등록."""

    @mcp.tool()
    def get_defect_by_equipment(
        date_start: str,
        date_end: str,
        line_type: str = "",
    ) -> str:
        """설비별 불량 현황 — 어떤 설비에서 불량이 많이 발생하는지.

        Args:
            date_start: 시작일 (YYYY-MM-DD)
            date_end: 종료일 (YYYY-MM-DD)
            line_type: 라인 타입 필터. 빈 문자열이면 전체.
        """
        sql = """
        SELECT
            e.equip_id AS 설비ID,
            e.equip_name AS 설비명,
            e.equip_type AS 설비유형,
            pline.line_type AS 라인,
            COUNT(*) AS 불량건수,
            GROUP_CONCAT(DISTINCT dr.defect_type) AS 불량유형목록
        FROM DEFECT_RECORDS dr
        JOIN EQUIPMENT e ON dr.equip_id = e.equip_id
        JOIN PRODUCTION_LINES pline ON e.line_id = pline.line_id
        JOIN PRODUCTION_LOG pl ON dr.log_id = pl.log_id
        JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
        WHERE wo.order_date BETWEEN ? AND ?
        """
        params = [date_start, date_end]
        if line_type:
            sql += " AND pline.line_type = ?"
            params.append(line_type.upper())
        sql += " GROUP BY e.equip_id, e.equip_name, e.equip_type, pline.line_type ORDER BY 불량건수 DESC"
        return to_json(query(sql, tuple(params)))

    @mcp.tool()
    def get_equipment_downtime(
        date_start: str,
        date_end: str,
        line_type: str = "",
        reason_code: str = "",
    ) -> str:
        """설비 비가동 현황 — 사유별 발생횟수와 비가동 시간.

        Args:
            date_start: 시작일 (YYYY-MM-DD)
            date_end: 종료일 (YYYY-MM-DD)
            line_type: 라인 타입 필터. 빈 문자열이면 전체.
            reason_code: 사유코드 필터 (BREAKDOWN/MATERIAL/MOLD_CHANGE/PM/EMERGENCY). 빈 문자열이면 전체.
        """
        sql = """
        SELECT
            e.equip_name AS 설비명,
            e.equip_type AS 설비유형,
            pline.line_type AS 라인,
            ed.reason_code AS 사유코드,
            ed.reason_detail AS 사유상세,
            COUNT(*) AS 발생횟수,
            ROUND(SUM(
                (julianday(COALESCE(ed.end_time, datetime('now'))) - julianday(ed.start_time)) * 24
            ), 2) AS 비가동시간_h
        FROM EQUIPMENT_DOWNTIME ed
        JOIN EQUIPMENT e ON ed.equip_id = e.equip_id
        JOIN PRODUCTION_LINES pline ON e.line_id = pline.line_id
        WHERE date(ed.start_time) BETWEEN ? AND ?
        """
        params = [date_start, date_end]
        if line_type:
            sql += " AND pline.line_type = ?"
            params.append(line_type.upper())
        if reason_code:
            sql += " AND ed.reason_code = ?"
            params.append(reason_code.upper())
        sql += " GROUP BY e.equip_name, e.equip_type, pline.line_type, ed.reason_code, ed.reason_detail ORDER BY 비가동시간_h DESC"
        return to_json(query(sql, tuple(params)))

    @mcp.tool()
    def get_maintenance_history(
        date_start: str = "",
        date_end: str = "",
        equip_id: int = 0,
        top_n: int = 20,
    ) -> str:
        """설비 정비 이력 조회.

        Args:
            date_start: 시작일 (YYYY-MM-DD). 빈 문자열이면 전체.
            date_end: 종료일 (YYYY-MM-DD). 빈 문자열이면 전체.
            equip_id: 설비 ID. 0이면 전체.
            top_n: 최대 조회 건수. 기본 20.
        """
        sql = """
        SELECT
            mh.maint_date AS 정비일,
            e.equip_name AS 설비명,
            e.equip_type AS 설비유형,
            pline.line_type AS 라인,
            mh.maint_type AS 정비유형,
            mh.description AS 정비내용,
            mh.cost AS 비용
        FROM MAINTENANCE_HISTORY mh
        JOIN EQUIPMENT e ON mh.equip_id = e.equip_id
        JOIN PRODUCTION_LINES pline ON e.line_id = pline.line_id
        WHERE 1=1
        """
        params = []
        if equip_id:
            sql += " AND mh.equip_id = ?"
            params.append(equip_id)
        if date_start:
            sql += " AND mh.maint_date >= ?"
            params.append(date_start)
        if date_end:
            sql += " AND mh.maint_date <= ?"
            params.append(date_end)
        sql += f" ORDER BY mh.maint_date DESC LIMIT {int(top_n)}"
        return to_json(query(sql, tuple(params)))

    @mcp.tool()
    def get_process_params_anomaly(
        date_start: str,
        date_end: str,
        equip_id: int = 0,
    ) -> str:
        """공정 파라미터 이상치 조회 — 상한/하한 초과 측정값.

        Args:
            date_start: 시작일 (YYYY-MM-DD)
            date_end: 종료일 (YYYY-MM-DD)
            equip_id: 설비 ID. 0이면 전체.
        """
        sql = """
        SELECT
            e.equip_name AS 설비명,
            pp.param_name AS 파라미터,
            pp.param_value AS 측정값,
            pp.lower_limit AS 하한,
            pp.upper_limit AS 상한,
            CASE
                WHEN pp.param_value > pp.upper_limit THEN '상한초과'
                WHEN pp.param_value < pp.lower_limit THEN '하한미달'
            END AS 이상유형,
            date(pl.start_time) AS 측정일
        FROM PROCESS_PARAMS pp
        JOIN EQUIPMENT e ON pp.equip_id = e.equip_id
        JOIN PRODUCTION_LOG pl ON pp.log_id = pl.log_id
        JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
        WHERE wo.order_date BETWEEN ? AND ?
          AND (pp.param_value > pp.upper_limit OR pp.param_value < pp.lower_limit)
        """
        params = [date_start, date_end]
        if equip_id:
            sql += " AND pp.equip_id = ?"
            params.append(equip_id)
        sql += " ORDER BY 측정일 DESC"
        return to_json(query(sql, tuple(params)))
