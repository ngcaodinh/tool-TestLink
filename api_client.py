"""
TestLink API Client - XML-RPC wrapper and MySQL database accessor
"""
import xmlrpc.client
import mysql.connector
from mysql.connector import Error
from typing import Optional, List, Dict, Any
from config import TESTLINK_URL, DB_HOST, DB_USER, DB_PASS, DB_NAME


class TestLinkClient:
    def __init__(self, dev_key: Optional[str] = None):
        self.dev_key = dev_key
        self.server = None
        self.db_connection = None

    def connect(self, dev_key: Optional[str] = None) -> bool:
        if dev_key:
            self.dev_key = dev_key
        if not self.dev_key:
            return False
        try:
            self.server = xmlrpc.client.ServerProxy(TESTLINK_URL, allow_none=True)
            self.server.tl.ping({"devKey": self.dev_key})
            return True
        except Exception as e:
            print(f"XML-RPC Connection Error: {e}")
            return False

    def _rpc_call(self, method: str, args: Dict[str, Any] = None):
        if not self.server:
            raise ConnectionError("Not connected to TestLink server")
        if args is None:
            args = {}
        args["devKey"] = self.dev_key
        rpc_method = getattr(self.server.tl, method)
        return rpc_method(args)

    def connect_db(self) -> bool:
        try:
            self.db_connection = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME
            )
            return True
        except Error as e:
            print(f"Database Connection Error: {e}")
            return False

    def close_db(self):
        if self.db_connection and self.db_connection.is_connected():
            self.db_connection.close()

    def _db_query(self, query: str, params: tuple = None) -> List[Dict]:
        if not self.db_connection or not self.db_connection.is_connected():
            self.connect_db()
        cursor = self.db_connection.cursor(dictionary=True)
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()
        return result

    def _db_execute(self, query: str, params: tuple = None) -> int:
        if not self.db_connection or not self.db_connection.is_connected():
            self.connect_db()
        cursor = self.db_connection.cursor()
        cursor.execute(query, params)
        self.db_connection.commit()
        last_id = cursor.lastrowid
        cursor.close()
        return last_id

    # XML-RPC Methods
    def about(self) -> Dict:
        return self._rpc_call("about")

    def get_projects(self) -> List[Dict]:
        return self._rpc_call("getProjects")

    def get_project_by_name(self, name: str) -> Dict:
        return self._rpc_call("getTestProjectByName", {"testprojectname": name})

    def create_project(self, name: str, prefix: str, description: str = "") -> Dict:
        return self._rpc_call("createTestProject", {
            "testprojectname": name,
            "testcaseprefix": prefix,
            "notes": description
        })

    def get_plans(self, project_id: int) -> List[Dict]:
        return self._rpc_call("getProjectTestPlans", {"testprojectid": project_id})

    def get_plan_by_name(self, project_name: str, plan_name: str) -> Dict:
        return self._rpc_call("getTestPlanByName", {
            "testprojectname": project_name,
            "testplanname": plan_name
        })

    def create_plan(self, project_name: str, plan_name: str, description: str = "", notes: str = "") -> Dict:
        return self._rpc_call("createTestPlan", {
            "testprojectname": project_name,
            "testplanname": plan_name,
            "plannotes": description,
            "notes": notes
        })

    def get_suites(self, project_id: int) -> List[Dict]:
        return self._rpc_call("getFirstLevelTestSuitesForTestProject", {"testprojectid": project_id})

    def get_suite_by_name(self, project_name: str, suite_name: str) -> Dict:
        return self._rpc_call("getTestSuiteByName", {
            "testprojectname": project_name,
            "testsuitename": suite_name
        })

    def create_suite(self, project_prefix: str, suite_name: str, details: str = "", parent_suite_id: int = None) -> Dict:
        params = {
            "prefix": project_prefix,
            "testsuitename": suite_name,
            "details": details
        }
        if parent_suite_id:
            params["parentid"] = parent_suite_id
        return self._rpc_call("createTestSuite", params)

    def get_testcases(self, suite_id: int, deep: bool = True) -> List[Dict]:
        return self._rpc_call("getTestCasesForTestSuite", {"testsuiteid": suite_id, "deep": deep})

    def get_cases_for_plan(self, plan_id: int) -> List[Dict]:
        return self._rpc_call("getTestCasesForTestPlan", {"testplanid": plan_id})

    def get_testcase_by_external_id(self, external_id: str) -> Dict:
        return self._rpc_call("getTestCase", {"testcaseexternalid": external_id})

    def get_testcase_by_id(self, testcaseid: int) -> Dict:
        return self._rpc_call("getTestCase", {"testcaseid": testcaseid})

    def create_testcase(self, suite_id: int, name: str, summary: str, steps: List[Dict],
                        expected_results: List[str], project_id: int = None,
                        keywords: List[str] = None,
                        author_login: str = None) -> Dict:
        action_list = []
        expected_list = []
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                action_list.append({"step_number": i + 1, "actions": step.get("actions", step.get("step", ""))})
                expected_list.append(step.get("expected_results", expected_results[i] if i < len(expected_results) else ""))
            else:
                action_list.append({"step_number": i + 1, "actions": str(step)})
                expected_list.append(expected_results[i] if i < len(expected_results) else "")

        params = {
            "testsuiteid": suite_id,
            "testcasename": name,
            "summary": summary,
            "steps": action_list,
            "expected_results": expected_list
        }
        if project_id:
            params["testprojectid"] = project_id
        if keywords:
            params["keywords"] = keywords
        if author_login is None:
            try:
                author_login = self.get_current_user()
            except Exception:
                author_login = None
        if author_login:
            params["authorlogin"] = author_login

        return self._rpc_call("createTestCase", params)

    def create_testcase_with_check(self, suite_id: int, name: str, summary: str, steps: List[Dict],
                                   expected_results: List[str], project_id: int = None,
                                   keywords: List[str] = None,
                                   author_login: str = None) -> Dict:
        result = self.create_testcase(suite_id, name, summary, steps, expected_results,
                                      project_id, keywords, author_login)
        # TestLink API returns list of dicts: [{'code': ..., 'message': ...}] on error,
        # or [{'status_ok': True, 'id': ..., ...}] on success
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict):
                if 'status_ok' in first and not first.get('status_ok'):
                    raise Exception(first.get("message", str(result)))
                if 'code' in first and first.get('code', 0) >= 0 and 'message' in first and first.get('status_ok', True) is False:
                    raise Exception(f"code {first['code']}: {first['message']}")
                if first.get('code') and first.get('code') not in (0, 200) and not first.get('status_ok', True):
                    raise Exception(f"code {first['code']}: {first['message']}")
        elif isinstance(result, dict):
            if not result.get("status_ok", True):
                raise Exception(result.get("message", str(result)))
        return result

    def get_current_user(self) -> str:
        if not self.db_connection:
            self.connect_db()
        if not self.db_connection:
            return ""
        query = "SELECT login FROM users WHERE active=1 LIMIT 1"
        result = self._db_query(query)
        return result[0]['login'] if result else ""

    def add_case_to_plan(self, plan_id: int, case_external_id: str, version: int = 1) -> Dict:
        return self._rpc_call("addTestCaseToTestPlan", {
            "testplanid": plan_id,
            "externalid": case_external_id,
            "version": version
        })

    def get_builds(self, plan_id: int) -> List[Dict]:
        return self._rpc_call("getBuildsForTestPlan", {"testplanid": plan_id})

    def create_build(self, plan_id: int, build_name: str, notes: str = "") -> Dict:
        return self._rpc_call("createBuild", {
            "testplanid": plan_id,
            "buildname": build_name,
            "notes": notes
        })

    def get_testers(self) -> List[Dict]:
        return self._rpc_call("getUserByLogin", {"userid": "all"})

    def get_user_by_login(self, login: str) -> Dict:
        return self._rpc_call("getUserByLogin", {"userlogin": login})

    def report_result(self, plan_id: int, build_id: int, case_external_id: str,
                      status: str, notes: str = "", tester_id: int = None) -> Dict:
        # Extract numeric part from external ID (e.g., "PRJ-1" -> 1)
        numeric_id = case_external_id
        if '-' in str(case_external_id):
            parts = str(case_external_id).rsplit('-', 1)
            numeric_id = parts[-1]
        
        params = {
            "testplanid": plan_id,
            "buildid": build_id,
            "externalid": numeric_id,
            "status": status,
            "notes": notes
        }
        if tester_id:
            params["userid"] = tester_id
        
        result = self._rpc_call("reportTCResult", params)
        print(f"DEBUG reportTCResult: case_external_id={case_external_id} -> numeric_id={numeric_id}, result={result}")
        return result

    def get_last_execution_result(self, plan_id: int, case_external_id: str) -> Dict:
        return self._rpc_call("getLastExecutionResult", {
            "testplanid": plan_id,
            "externalid": case_external_id
        })

    # Database Query Methods for Reports
    def get_execution_notes(self, plan_id: int, build_id: int = None) -> List[Dict]:
        query = """
            SELECT e.id, e.tcversion_id, e.status, e.notes, e.execution_ts,
                   nh_tc.name as tc_name, b.name as build_name, u.login as tester
            FROM executions e
            JOIN tcversions tcv ON e.tcversion_id = tcv.id
            JOIN nodes_hierarchy nh_v ON tcv.id = nh_v.id AND nh_v.node_type_id = 4
            JOIN nodes_hierarchy nh_tc ON nh_v.parent_id = nh_tc.id AND nh_tc.node_type_id = 3
            JOIN builds b ON e.build_id = b.id
            LEFT JOIN users u ON e.tester_id = u.id
            WHERE e.testplan_id = %s
        """
        params = [plan_id]
        if build_id:
            query += " AND e.build_id = %s"
            params.append(build_id)
        query += " ORDER BY e.execution_ts DESC"
        return self._db_query(query, tuple(params))

    def get_step_results(self, execution_id: int) -> List[Dict]:
        query = """
            SELECT ets.id, ets.step_id, ets.status, ets.notes,
                   ts.step_number, ts.actions, ts.expected_results
            FROM execution_tcsteps ets
            JOIN tcsteps ts ON ets.step_id = ts.id
            WHERE ets.execution_id = %s
            ORDER BY ts.step_number
        """
        return self._db_query(query, (execution_id,))

    def get_tc_custom_fields(self, tc_id: int, version_id: int = None) -> List[Dict]:
        query = """
            SELECT cf.name, cf.label, cfv.value
            FROM cfield_design_values cfv
            JOIN custom_fields cf ON cfv.field_id = cf.id
            WHERE cfv.node_id = %s
        """
        params = [tc_id]
        if version_id:
            query += " OR (cfv.node_id = %s AND cfv.version = %s)"
            params.extend([tc_id, version_id])
        return self._db_query(query, tuple(params))

    def get_requirements_coverage(self, tc_id: int) -> List[Dict]:
        query = """
            SELECT r.id, r.title, r.req_doc_id, rs.title as spec_title
            FROM req_coverage rc
            JOIN requirements r ON rc.req_id = r.id
            JOIN req_specs rs ON r.srs_id = rs.id
            WHERE rc.testcase_id = %s
        """
        return self._db_query(query, (tc_id,))

    def get_all_plan_executions(self, plan_id: int, build_id: int = None) -> List[Dict]:
        query = """
            SELECT e.id, e.tcversion_id, e.status, e.notes, e.execution_ts,
                   nh_tc.name as tc_name, b.name as build_name, u.login as tester,
                   tcv.version, tcv.summary
            FROM executions e
            JOIN tcversions tcv ON e.tcversion_id = tcv.id
            JOIN nodes_hierarchy nh_v ON tcv.id = nh_v.id AND nh_v.node_type_id = 4
            JOIN nodes_hierarchy nh_tc ON nh_v.parent_id = nh_tc.id AND nh_tc.node_type_id = 3
            JOIN builds b ON e.build_id = b.id
            LEFT JOIN users u ON e.tester_id = u.id
            WHERE e.testplan_id = %s
        """
        params = [plan_id]
        if build_id:
            query += " AND e.build_id = %s"
            params.append(build_id)
        query += " ORDER BY nh_tc.name, e.execution_ts DESC"
        return self._db_query(query, tuple(params))

    def get_plan_metrics(self, plan_id: int, build_id: int = None) -> Dict:
        query = """
            SELECT
                COUNT(DISTINCT e.tcversion_id) as total_tcs,
                SUM(CASE WHEN e.status = 'p' THEN 1 ELSE 0 END) as passed,
                SUM(CASE WHEN e.status = 'f' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN e.status = 'b' THEN 1 ELSE 0 END) as blocked,
                SUM(CASE WHEN e.status = 'w' THEN 1 ELSE 0 END) as warning,
                SUM(CASE WHEN e.status = 'n' THEN 1 ELSE 0 END) as not_run,
                COUNT(DISTINCT e.build_id) as total_builds
            FROM executions e
            WHERE e.testplan_id = %s
        """
        params = [plan_id]
        if build_id:
            query += " AND e.build_id = %s"
            params.append(build_id)
        result = self._db_query(query, tuple(params))
        if result:
            return result[0]
        return {}

    def get_tc_keywords(self, tc_id: int) -> List[Dict]:
        query = """
            SELECT k.keyword, k.notes
            FROM testcase_keywords tck
            JOIN keywords k ON tck.keyword_id = k.id
            WHERE tck.testcase_id = %s
        """
        return self._db_query(query, (tc_id,))

    def get_tc_author(self, tc_id: int) -> Dict:
        query = """
            SELECT u.login, u.first_name, u.last_name, u.email
            FROM tcversions tcv
            JOIN nodes_hierarchy nh_v ON tcv.id = nh_v.id AND nh_v.node_type_id = 4
            JOIN users u ON tcv.author_id = u.id
            WHERE nh_v.parent_id = %s
            ORDER BY tcv.version DESC
            LIMIT 1
        """
        result = self._db_query(query, (tc_id,))
        return result[0] if result else {}

    def get_tc_steps(self, tcversion_id: int) -> List[Dict]:
        query = """
            SELECT id, step_number, actions, expected_results
            FROM tcsteps
            WHERE tcversion_id = %s
            ORDER BY step_number
        """
        return self._db_query(query, (tcversion_id,))

    def get_build_custom_fields(self, build_id: int) -> List[Dict]:
        query = """
            SELECT cf.name, cf.label, cfv.value
            FROM cfield_execution_values cfv
            JOIN custom_fields cf ON cfv.field_id = cf.id
            WHERE cfv.execution_id = %s
        """
        return self._db_query(query, (build_id,))

    def get_executions(self, plan_id: int, build_id: int = None) -> List[Dict]:
        query = """
            SELECT e.id, e.tcversion_id, e.status, e.notes, e.execution_ts,
                   nh_tc.name as tc_name, b.name as build_name, u.login as tester
            FROM executions e
            JOIN tcversions tcv ON e.tcversion_id = tcv.id
            JOIN nodes_hierarchy nh_v ON tcv.id = nh_v.id AND nh_v.node_type_id = 4
            JOIN nodes_hierarchy nh_tc ON nh_v.parent_id = nh_tc.id AND nh_tc.node_type_id = 3
            JOIN builds b ON e.build_id = b.id
            LEFT JOIN users u ON e.tester_id = u.id
            WHERE e.testplan_id = %s
        """
        params = [plan_id]
        if build_id:
            query += " AND e.build_id = %s"
            params.append(build_id)
        query += " ORDER BY e.execution_ts DESC"
        return self._db_query(query, tuple(params))

    def get_suite_details(self, suite_id: int) -> Dict:
        query = """
            SELECT nh.id, nh.name, nh.parent_id, ts.details
            FROM nodes_hierarchy nh
            JOIN testsuites ts ON nh.id = ts.id
            WHERE nh.id = %s
        """
        result = self._db_query(query, (suite_id,))
        return result[0] if result else {}

    def get_testcases_in_suite(self, suite_id: int) -> List[Dict]:
        query = """
            SELECT nh.id AS tc_id, nh.name, 1 AS version, '' AS summary,
                   nh.node_order, nh.node_type_id
            FROM nodes_hierarchy nh
            WHERE nh.parent_id = %s AND nh.node_type_id = 3
        """
        return self._db_query(query, (suite_id,))

    def get_testcases_in_project(self, project_id: int) -> List[Dict]:
        query = """
            SELECT nh_tc.id AS tc_id, nh_tc.name, 1 AS version, '' AS summary,
                   nh_tc.node_order, nh_tc.node_type_id,
                   nh_suite.id AS suite_id, nh_suite.name AS suite_name
            FROM nodes_hierarchy nh_project
            JOIN nodes_hierarchy nh_suite
                ON nh_suite.parent_id = nh_project.id AND nh_suite.node_type_id = 2
            JOIN nodes_hierarchy nh_tc
                ON nh_tc.parent_id = nh_suite.id AND nh_tc.node_type_id = 3
            WHERE nh_project.id = %s AND nh_project.node_type_id = 1
        """
        return self._db_query(query, (project_id,))

    def get_testcase_by_id(self, tc_id: int) -> Dict:
        query = """
            SELECT nh.id AS tc_id, nh.name, nh.node_order, nh.node_type_id,
                   nh.parent_id AS suite_id, p.name AS suite_name,
                   pr.id AS project_id, pr.name AS project_name
            FROM nodes_hierarchy nh
            JOIN nodes_hierarchy p ON p.id = nh.parent_id
            JOIN nodes_hierarchy pr ON pr.id = p.parent_id
            WHERE nh.id = %s AND nh.node_type_id = 3
        """
        result = self._db_query(query, (tc_id,))
        return result[0] if result else {}

    # ==================== REQUIREMENTS ====================

    def get_req_specs(self, project_id: int) -> List[Dict]:
        query = """
            SELECT rs.id, rs.doc_id, rs.testproject_id,
                   nh.name, nh.parent_id, nh.node_order,
                   rsrev.revision, rsrev.scope, rsrev.type AS spec_type,
                   rsrev.total_req
            FROM req_specs rs
            JOIN nodes_hierarchy nh ON nh.id = rs.id
            LEFT JOIN req_specs_revisions rsrev ON rsrev.id = rs.id
            WHERE rs.testproject_id = %s
            ORDER BY nh.node_order, nh.name
        """
        return self._db_query(query, (project_id,))

    def get_all_requirements(self, project_id: int) -> List[Dict]:
        query = """
            SELECT r.id, r.srs_id, r.req_doc_id,
                   nh.name, nh.node_order,
                   srs.doc_id AS spec_doc_id,
                   srsnh.name AS spec_name,
                   rv.version, rv.revision, rv.scope, rv.status, rv.type,
                   rv.expected_coverage, rv.author_id,
                   u.login AS author_login
            FROM requirements r
            JOIN nodes_hierarchy nh ON nh.id = r.id
            JOIN req_specs srs ON srs.id = r.srs_id
            JOIN nodes_hierarchy srsnh ON srsnh.id = srs.id
            JOIN req_versions rv ON rv.id = r.id
            LEFT JOIN users u ON u.id = rv.author_id
            WHERE srs.testproject_id = %s
            ORDER BY srsnh.name, nh.node_order, nh.name
        """
        return self._db_query(query, (project_id,))

    def get_requirements_in_spec(self, spec_id: int) -> List[Dict]:
        query = """
            SELECT r.id, r.srs_id, r.req_doc_id,
                   nh.name, nh.node_order,
                   rv.version, rv.revision, rv.scope, rv.status, rv.type,
                   rv.expected_coverage, rv.author_id,
                   u.login AS author_login
            FROM requirements r
            JOIN nodes_hierarchy nh ON nh.id = r.id
            JOIN nodes_hierarchy ver_nh ON ver_nh.parent_id = r.id AND ver_nh.node_type_id = 8
            JOIN req_versions rv ON rv.id = ver_nh.id
            LEFT JOIN users u ON u.id = rv.author_id
            WHERE r.srs_id = %s
            ORDER BY nh.node_order, nh.name
        """
        return self._db_query(query, (spec_id,))

    def create_req_spec(self, project_id: int, doc_id: str, title: str,
                        scope: str = '', spec_type: str = 'N',
                        user_id: int = None) -> Dict:
        if user_id is None:
            user_id = self._get_user_id()
        if not user_id:
            return {"status_ok": False, "msg": "Cannot determine user_id"}

        title = title.strip()[:100]
        doc_id = doc_id.strip()[:64]

        if not self.db_connection or not self.db_connection.is_connected():
            self.connect_db()

        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                "SELECT COALESCE(MAX(node_order), 0) + 1 FROM nodes_hierarchy WHERE parent_id = %s",
                (project_id,)
            )
            node_order = cursor.fetchone()[0]
        except Exception:
            node_order = 0

        # 1. nodes_hierarchy entry for spec (node_type_id=6)
        cursor.execute(
            "INSERT INTO nodes_hierarchy (parent_id, node_type_id, name, node_order) VALUES (%s, 6, %s, %s)",
            (project_id, title, node_order)
        )
        spec_id = cursor.lastrowid

        # 2. req_specs (shares id with nodes_hierarchy)
        cursor.execute(
            "INSERT INTO req_specs (id, testproject_id, doc_id) VALUES (%s, %s, %s)",
            (spec_id, project_id, doc_id)
        )

        # 3. nodes_hierarchy entry for revision (node_type_id=11), parent=spec_id
        cursor.execute(
            "INSERT INTO nodes_hierarchy (parent_id, node_type_id, name, node_order) VALUES (%s, 11, %s, 0)",
            (spec_id, title)
        )
        rev_id = cursor.lastrowid

        # 4. req_specs_revisions (shares id with revision nodes_hierarchy)
        cursor.execute(
            "INSERT INTO req_specs_revisions "
            "(parent_id, id, revision, doc_id, name, scope, type, total_req, status, author_id, log_message) "
            "VALUES (%s, %s, 1, %s, %s, %s, %s, 0, 1, %s, %s)",
            (spec_id, rev_id, doc_id, title, scope, spec_type, user_id,
             'Requirement specification created')
        )

        self.db_connection.commit()
        cursor.close()
        return {"status_ok": True, "id": spec_id, "revision_id": rev_id, "msg": "Req Spec created"}

    def create_requirement(self, spec_id: int, req_doc_id: str, title: str,
                           scope: str = '', status: str = 'V', req_type: str = 'I',
                           expected_coverage: int = 1, user_id: int = None) -> Dict:
        if user_id is None:
            user_id = self._get_user_id()
        if not user_id:
            return {"status_ok": False, "msg": "Cannot determine user_id"}

        title = title.strip()[:64]
        req_doc_id = req_doc_id.strip()[:64]

        if not self.db_connection or not self.db_connection.is_connected():
            self.connect_db()

        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                "SELECT COALESCE(MAX(node_order), 0) + 1 FROM nodes_hierarchy WHERE parent_id = %s",
                (spec_id,)
            )
            node_order = cursor.fetchone()[0]
        except Exception:
            node_order = 0

        # 1. nodes_hierarchy entry for requirement (node_type_id=7), parent=spec_id
        cursor.execute(
            "INSERT INTO nodes_hierarchy (parent_id, node_type_id, name, node_order) VALUES (%s, 7, %s, %s)",
            (spec_id, title, node_order)
        )
        req_id = cursor.lastrowid

        # 2. requirements (shares id with nodes_hierarchy)
        cursor.execute(
            "INSERT INTO requirements (id, srs_id, req_doc_id) VALUES (%s, %s, %s)",
            (req_id, spec_id, req_doc_id)
        )

        # 3. nodes_hierarchy entry for version (node_type_id=8), parent=req_id
        cursor.execute(
            "INSERT INTO nodes_hierarchy (parent_id, node_type_id, name, node_order) VALUES (%s, 8, '', 0)",
            (req_id,)
        )
        ver_id = cursor.lastrowid

        # 4. req_versions (shares id with version nodes_hierarchy)
        cursor.execute(
            "INSERT INTO req_versions "
            "(id, version, revision, scope, status, type, expected_coverage, author_id, log_message) "
            "VALUES (%s, 1, 1, %s, %s, %s, %s, %s, %s)",
            (ver_id, scope, status, req_type, expected_coverage, user_id, 'Requirement created')
        )

        self.db_connection.commit()
        cursor.close()
        return {"status_ok": True, "id": req_id, "version_id": ver_id, "msg": "Requirement created"}

    def get_req_spec_detail(self, spec_id: int) -> Dict:
        """Get spec with full info including revision"""
        query = """
            SELECT rs.id, rs.doc_id, rs.testproject_id,
                   rsr.id as revision_id, rsr.revision, rsr.scope, rsr.type,
                   rsr.total_req, rsr.status, rsr.author_id,
                   rsr.creation_ts, rsr.modifier_id, rsr.modification_ts,
                   nh.name as title, nh.node_order
            FROM req_specs rs
            JOIN req_specs_revisions rsr ON rsr.parent_id = rs.id
            JOIN nodes_hierarchy nh ON nh.id = rs.id
            WHERE rs.id = %s
            ORDER BY rsr.revision DESC
            LIMIT 1
        """
        rows = self._db_query(query, (spec_id,))
        return rows[0] if rows else {}

    def get_requirements_with_coverage(self, spec_id: int) -> List[Dict]:
        """Get requirements in spec with coverage info"""
        query = """
            SELECT r.id, r.srs_id, r.req_doc_id,
                   nh.name, nh.node_order,
                   rv.version, rv.revision, rv.scope, rv.status, rv.type,
                   rv.expected_coverage, rv.author_id,
                   u.login AS author_login,
                   (SELECT COUNT(*) FROM req_coverage rc WHERE rc.req_id = r.id) AS tc_count
            FROM requirements r
            JOIN nodes_hierarchy nh ON nh.id = r.id
            JOIN req_versions rv ON rv.id = (
                SELECT id FROM nodes_hierarchy WHERE parent_id = r.id AND node_type_id = 8 ORDER BY id DESC LIMIT 1
            )
            LEFT JOIN users u ON u.id = rv.author_id
            WHERE r.srs_id = %s
            ORDER BY nh.node_order, nh.name
        """
        return self._db_query(query, (spec_id,))

    def get_testcases_for_assign(self, project_id: int) -> List[Dict]:
        """Get test cases in project for assign modal"""
        query = """
            SELECT tc.id, tc.version, nh.name, nh.parent_id,
                   nh2.name as suite_name
            FROM nodes_hierarchy nh
            JOIN tcversions tc ON tc.id = nh.id
            JOIN nodes_hierarchy nh2 ON nh2.id = nh.parent_id
            WHERE nh.node_type_id = 4
            AND EXISTS (
                SELECT 1 FROM nodes_hierarchy WHERE parent_id = %s AND node_type_id = 2
            )
            ORDER BY nh2.name, nh.node_order
        """
        return self._db_query(query, (project_id,))

    def update_req_spec(self, spec_id: int, doc_id: str, title: str, scope: str,
                        spec_type: str, user_id: int = None) -> Dict:
        """Update req_specs and nodes_hierarchy"""
        if user_id is None:
            user_id = self._get_user_id()
        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                "UPDATE nodes_hierarchy SET name = %s WHERE id = %s",
                (title, spec_id)
            )
            cursor.execute(
                "UPDATE req_specs SET doc_id = %s WHERE id = %s",
                (doc_id, spec_id)
            )
            cursor.execute(
                "SELECT id FROM req_specs_revisions WHERE parent_id = %s ORDER BY revision DESC LIMIT 1",
                (spec_id,)
            )
            rev_row = cursor.fetchone()
            if rev_row:
                rev_id = rev_row[0]
                cursor.execute(
                    "UPDATE req_specs_revisions SET doc_id=%s, name=%s, scope=%s, type=%s, modifier_id=%s, modification_ts=NOW() WHERE id=%s",
                    (doc_id, title, scope, spec_type, user_id, rev_id)
                )
            self.db_connection.commit()
            return {"status_ok": True, "msg": "Updated"}
        except Exception as e:
            self.db_connection.rollback()
            return {"status_ok": False, "msg": str(e)}
        finally:
            cursor.close()

    def delete_req_spec(self, spec_id: int) -> Dict:
        """Delete spec and all children recursively"""
        cursor = self.db_connection.cursor()
        try:
            cursor.execute("""
                WITH RECURSIVE descendants AS (
                    SELECT id FROM nodes_hierarchy WHERE parent_id = %s
                    UNION ALL
                    SELECT nh.id FROM nodes_hierarchy nh JOIN descendants d ON nh.parent_id = d.id
                )
                SELECT id FROM descendants
            """, (spec_id,))
            child_ids = [row[0] for row in cursor.fetchall()]

            all_ids = child_ids + [spec_id]
            placeholders = ','.join(['%s'] * len(all_ids))

            # Delete req_versions via nodes_hierarchy
            cursor.execute(
                f"SELECT id FROM nodes_hierarchy WHERE parent_id IN ({placeholders}) AND node_type_id = 8",
                all_ids
            )
            ver_ids = [row[0] for row in cursor.fetchall()]
            if ver_ids:
                ver_placeholders = ','.join(['%s'] * len(ver_ids))
                cursor.execute(f"DELETE FROM req_versions WHERE id IN ({ver_placeholders})", ver_ids)

            # Delete requirements via nodes_hierarchy
            cursor.execute(
                f"SELECT id FROM nodes_hierarchy WHERE parent_id IN ({placeholders}) AND node_type_id = 7",
                all_ids
            )
            req_ids = [row[0] for row in cursor.fetchall()]
            if req_ids:
                req_placeholders = ','.join(['%s'] * len(req_ids))
                cursor.execute(f"DELETE FROM req_coverage WHERE req_id IN ({req_placeholders})", req_ids)
                cursor.execute(f"DELETE FROM requirements WHERE id IN ({req_placeholders})", req_ids)

            cursor.execute(f"DELETE FROM nodes_hierarchy WHERE id IN ({placeholders})", all_ids)
            cursor.execute(f"DELETE FROM req_specs WHERE id = %s", (spec_id,))

            self.db_connection.commit()
            return {"status_ok": True, "msg": "Deleted"}
        except Exception as e:
            self.db_connection.rollback()
            return {"status_ok": False, "msg": str(e)}
        finally:
            cursor.close()

    def _get_user_id(self) -> int:
        if not self.db_connection or not self.db_connection.is_connected():
            self.connect_db()
        cursor = self.db_connection.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE active = 1 LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        return row['id'] if row else 0

    # ==================== REQUIREMENT COVERAGE ====================

    def assign_testcases_to_req(self, req_id: int, testcase_ids: List[int],
                                user_id: int = None) -> Dict:
        if user_id is None:
            user_id = self._get_user_id()
        if not user_id:
            return {"status_ok": False, "msg": "Cannot determine user_id", "assigned": 0}

        if not self.db_connection or not self.db_connection.is_connected():
            self.connect_db()

        assigned = 0
        skipped = 0
        cursor = self.db_connection.cursor()
        for tc_id in testcase_ids:
            try:
                tc_id = int(tc_id)
                cursor.execute(
                    "SELECT 1 FROM req_coverage WHERE req_id=%s AND testcase_id=%s",
                    (req_id, tc_id)
                )
                if cursor.fetchone():
                    skipped += 1
                    continue
                cursor.execute(
                    "INSERT INTO req_coverage (req_id, testcase_id, author_id) VALUES (%s, %s, %s)",
                    (req_id, tc_id, user_id)
                )
                assigned += 1
            except Exception:
                skipped += 1
        self.db_connection.commit()
        cursor.close()
        return {
            "status_ok": True,
            "assigned": assigned,
            "skipped": skipped,
            "msg": f"Assigned {assigned}, skipped {skipped}"
        }

    def assign_testcases_to_spec(self, spec_id: int, testcase_ids: List[int],
                                  user_id: int = None) -> Dict:
        if user_id is None:
            user_id = self._get_user_id()
        if not user_id:
            return {"status_ok": False, "msg": "Cannot determine user_id", "assigned": 0}

        if not self.db_connection or not self.db_connection.is_connected():
            self.connect_db()

        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                "SELECT r.id FROM requirements r WHERE r.srs_id = %s",
                (spec_id,)
            )
            req_ids = [row[0] for row in cursor.fetchall()]
        except Exception:
            req_ids = []
        cursor.close()

        if not req_ids:
            return {"status_ok": False, "msg": "No requirements found in this spec", "assigned": 0}

        assigned = 0
        skipped = 0
        for req_id in req_ids:
            result = self.assign_testcases_to_req(req_id, testcase_ids, user_id)
            if result.get('status_ok'):
                assigned += result.get('assigned', 0)
                skipped += result.get('skipped', 0)

        return {
            "status_ok": True,
            "assigned": assigned,
            "skipped": skipped,
            "msg": f"Assigned to spec: {assigned} test case(s); skipped {skipped} already linked."
        }

    def get_requirements_for_assignment(self, project_id: int) -> List[Dict]:
        # Via parent chain: requirement -> parent spec -> project
        query = """
            SELECT DISTINCT
                r.id, r.req_doc_id, nh_r.name,
                nh_spec.id AS spec_id, nh_spec.name AS spec_name
            FROM requirements r
            JOIN nodes_hierarchy nh_r ON nh_r.id = r.id
            JOIN nodes_hierarchy nh_spec ON nh_spec.id = nh_r.parent_id
            JOIN nodes_hierarchy nh_proj ON nh_proj.id = nh_spec.parent_id
            WHERE nh_proj.id = %s
            ORDER BY spec_name, nh_r.name
        """
        return self._db_query(query, (project_id,))
        query = """
            SELECT DISTINCT nh_tc.id as tc_id, nh_tc.name, tcv.id as version_id, tcv.version,
                   tcv.summary, e.status, e.notes as execution_notes, e.execution_ts,
                   b.name as build_name, u.login as tester
            FROM testplan_tcversions tptc
            JOIN tcversions tcv ON tptc.tcversion_id = tcv.id
            JOIN nodes_hierarchy nh_v ON tcv.id = nh_v.id AND nh_v.node_type_id = 4
            JOIN nodes_hierarchy nh_tc ON nh_v.parent_id = nh_tc.id AND nh_tc.node_type_id = 3
            LEFT JOIN executions e ON e.tcversion_id = tcv.id AND e.testplan_id = tptc.testplan_id
            LEFT JOIN builds b ON e.build_id = b.id
            LEFT JOIN users u ON e.tester_id = u.id
            WHERE tptc.testplan_id = %s
        """
        params = [plan_id]
        if build_id:
            query += " AND (e.build_id = %s OR e.build_id IS NULL)"
            params.append(build_id)
        query += " ORDER BY nh_tc.name"
        return self._db_query(query, tuple(params))

    def get_recent_executions(self, limit: int = 10) -> List[Dict]:
        query = """
            SELECT e.id, e.status, e.execution_ts, e.notes,
                   nh_tc.name as tc_name, nh_plan.name as plan_name, b.name as build_name,
                   u.login as tester
            FROM executions e
            JOIN tcversions tcv ON e.tcversion_id = tcv.id
            JOIN nodes_hierarchy nh_v ON tcv.id = nh_v.id AND nh_v.node_type_id = 4
            JOIN nodes_hierarchy nh_tc ON nh_v.parent_id = nh_tc.id AND nh_tc.node_type_id = 3
            JOIN testplans tp ON e.testplan_id = tp.id
            JOIN nodes_hierarchy nh_plan ON tp.id = nh_plan.id AND nh_plan.node_type_id = 5
            JOIN builds b ON e.build_id = b.id
            LEFT JOIN users u ON e.tester_id = u.id
            ORDER BY e.execution_ts DESC
            LIMIT %s
        """
        return self._db_query(query, (limit,))

    def get_counts(self) -> Dict:
        counts = {}
        try:
            if not self.db_connection or not self.db_connection.is_connected():
                self.connect_db()

            cursor = self.db_connection.cursor()

            cursor.execute("SELECT COUNT(*) FROM testprojects WHERE active = 1")
            counts['projects'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM testplans WHERE active = 1")
            counts['plans'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM nodes_hierarchy WHERE node_type_id = 2")
            counts['suites'] = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(DISTINCT nh_parent.id)
                FROM tcversions tcv
                JOIN nodes_hierarchy nh ON tcv.id = nh.id
                JOIN nodes_hierarchy nh_parent ON nh.parent_id = nh_parent.id
                WHERE nh_parent.node_type_id = 3
            """)
            counts['testcases'] = cursor.fetchone()[0]

            cursor.close()
        except Error as e:
            print(f"Error getting counts: {e}")
            counts = {'projects': 0, 'plans': 0, 'suites': 0, 'testcases': 0}
        return counts

    def get_testcase_info(self, tc_id: int) -> Dict:
        """Get testcase info including whether it has executions."""
        query = """
            SELECT nh.id AS tc_id, nh.name, p.id AS project_id
            FROM nodes_hierarchy nh
            JOIN nodes_hierarchy p ON p.id = nh.parent_id
            WHERE nh.id = %s AND nh.node_type_id = 3
        """
        result = self._db_query(query, (tc_id,))
        return result[0] if result else {}

    def get_tcversions_for_testcase(self, tc_id: int) -> List[Dict]:
        """Get all versions of a testcase."""
        query = """
            SELECT id AS tcversion_id
            FROM nodes_hierarchy
            WHERE parent_id = %s AND node_type_id = 4
        """
        return self._db_query(query, (tc_id,))

    def has_executions(self, tc_id: int) -> bool:
        """Check if testcase has any executions."""
        query = """
            SELECT COUNT(*) as cnt
            FROM executions e
            JOIN tcversions tcv ON e.tcversion_id = tcv.id
            JOIN nodes_hierarchy nh_v ON tcv.id = nh_v.id AND nh_v.node_type_id = 4
            WHERE nh_v.parent_id = %s
        """
        result = self._db_query(query, (tc_id,))
        return result[0]['cnt'] > 0 if result else False

    def delete_testcase(self, tc_id: int) -> bool:
        """
        Delete a testcase and all its related data.
        Follows TestLink 1.9.16 deletion logic:
        1. Get all tcversion IDs for this testcase
        2. Delete execution data (execution_bugs, cfield_execution_values, executions)
        3. Delete testplan_tcversions and user_assignments
        4. Delete tcsteps and tcversions
        5. Delete testcase_keywords, req_coverage
        6. Delete attachments
        7. Delete from nodes_hierarchy (cascade)
        """
        if not self.db_connection or not self.db_connection.is_connected():
            self.connect_db()

        cursor = self.db_connection.cursor()
        try:
            tcversion_list = []
            step_list = []

            # Step 1: Get all tcversions and steps
            cursor.execute("""
                SELECT v.id AS tcversion_id, s.id AS step_id
                FROM nodes_hierarchy v
                LEFT JOIN nodes_hierarchy s ON s.parent_id = v.id
                WHERE v.parent_id = %s AND v.node_type_id = 4
            """, (tc_id,))
            for row in cursor.fetchall():
                tcversion_list.append(row[0])
                if row[1]:
                    step_list.append(row[1])

            if not tcversion_list:
                return False

            tcversions_str = ','.join(map(str, tcversion_list))
            steps_str = ','.join(map(str, step_list)) if step_list else None

            # Step 2: Delete execution data
            cursor.execute(f"""
                DELETE FROM execution_bugs
                WHERE execution_id IN (
                    SELECT id FROM executions WHERE tcversion_id IN ({tcversions_str})
                )
            """)

            cursor.execute(f"""
                DELETE FROM cfield_execution_values
                WHERE tcversion_id IN ({tcversions_str})
            """)

            cursor.execute(f"""
                DELETE FROM executions WHERE tcversion_id IN ({tcversions_str})
            """)

            # Step 3: Delete user_assignments and testplan_tcversions
            cursor.execute(f"""
                DELETE FROM user_assignments
                WHERE feature_id IN (
                    SELECT id FROM testplan_tcversions WHERE tcversion_id IN ({tcversions_str})
                )
            """)

            cursor.execute(f"""
                DELETE FROM testplan_tcversions WHERE tcversion_id IN ({tcversions_str})
            """)

            # Step 4: Delete tcsteps and tcversions
            if steps_str:
                cursor.execute(f"DELETE FROM tcsteps WHERE id IN ({steps_str})")

            cursor.execute(f"DELETE FROM tcversions WHERE id IN ({tcversions_str})")

            # Step 5: Delete testcase_keywords and req_coverage
            cursor.execute("DELETE FROM testcase_keywords WHERE testcase_id = %s", (tc_id,))
            cursor.execute("DELETE FROM req_coverage WHERE testcase_id = %s", (tc_id,))

            # Step 6: Delete custom field design values for this testcase and its versions
            for vid in tcversion_list:
                cursor.execute("DELETE FROM cfield_design_values WHERE node_id = %s", (vid,))
            cursor.execute("DELETE FROM cfield_design_values WHERE node_id = %s", (tc_id,))

            # Step 7: Delete from nodes_hierarchy (cascade will handle children)
            cursor.execute("DELETE FROM nodes_hierarchy WHERE id = %s", (tc_id,))

            self.db_connection.commit()
            cursor.close()
            return True

        except Error as e:
            print(f"Error deleting testcase: {e}")
            self.db_connection.rollback()
            cursor.close()
            return False
