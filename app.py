"""
TestLink Tool - Flask Web Application
"""
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import os
import json
import tempfile
from api_client import TestLinkClient
from report_generator import ReportGenerator
from config import FLASK_SECRET, HOST, PORT

app = Flask(__name__)
app.secret_key = FLASK_SECRET

client = TestLinkClient()


def init_client():
    if 'api_key' in session:
        client.connect(session['api_key'])
        client.connect_db()


@app.route('/')
def index():
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    init_client()
    try:
        client.connect_db()
        counts = client.get_counts()
        recent_executions = client.get_recent_executions(10)
    except Exception as e:
        counts = {'projects': 0, 'plans': 0, 'suites': 0, 'testcases': 0}
        recent_executions = []
        flash(f"Database connection error: {str(e)}", "error")
    
    api_connected = client.server is not None if client else False
    return render_template('dashboard.html', 
                         counts=counts, 
                         recent_executions=recent_executions,
                         api_connected=api_connected)


@app.route('/projects')
def projects():
    init_client()
    try:
        projects_list = client.get_projects()
    except Exception as e:
        projects_list = []
        flash(f"Error fetching projects: {str(e)}", "error")
    return render_template('projects.html', projects=projects_list)


@app.route('/projects/create', methods=['POST'])
def create_project():
    init_client()
    name = request.form.get('name', '').strip()
    prefix = request.form.get('prefix', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name or not prefix:
        flash("Name and Prefix are required", "error")
        return redirect(url_for('projects'))
    
    try:
        result = client.create_project(name, prefix, description)
        if result:
            flash(f"Project '{name}' created successfully", "success")
        else:
            flash("Failed to create project", "error")
    except Exception as e:
        flash(f"Error creating project: {str(e)}", "error")
    
    return redirect(url_for('projects'))


@app.route('/plans')
def plans():
    init_client()
    projects_list = []
    plans_list = []
    selected_project_id = request.args.get('project_id', type=int)
    
    try:
        projects_list = client.get_projects()
        if selected_project_id:
            plans_list = client.get_plans(selected_project_id)
        elif projects_list and len(projects_list) > 0:
            plans_list = client.get_plans(projects_list[0]['id'])
    except Exception as e:
        flash(f"Error fetching plans: {str(e)}", "error")
    
    return render_template('plans.html', 
                         projects=projects_list, 
                         plans=plans_list,
                         selected_project_id=selected_project_id)


@app.route('/plans/create', methods=['POST'])
def create_plan():
    init_client()
    project_id = request.form.get('project_id', type=int)
    project_name = request.form.get('project_name', '').strip()
    plan_name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    notes = request.form.get('notes', '').strip()

    if not project_id or not plan_name:
        flash("Project and Plan Name are required", "error")
        return redirect(url_for('plans'))

    try:
        result = client.create_plan(project_name, plan_name, description, notes)
        if result and not (isinstance(result, list) and result and 'code' in result[0]):
            flash(f"Test Plan '{plan_name}' created successfully", "success")
        else:
            err_msg = result[0]['message'] if isinstance(result, list) and result else "Failed to create test plan"
            flash(f"Failed to create test plan: {err_msg}", "error")
    except Exception as e:
        flash(f"Error creating plan: {str(e)}", "error")

    return redirect(url_for('plans') + f"?project_id={project_id}")


@app.route('/suites')
def suites():
    init_client()
    projects_list = []
    suites_list = []
    selected_project_id = request.args.get('project_id', type=int)
    
    try:
        projects_list = client.get_projects()
        if selected_project_id:
            suites_list = client.get_suites(selected_project_id)
        elif projects_list and len(projects_list) > 0:
            suites_list = client.get_suites(projects_list[0]['id'])
    except Exception as e:
        flash(f"Error fetching suites: {str(e)}", "error")
    
    return render_template('suites.html',
                         projects=projects_list,
                         suites=suites_list,
                         selected_project_id=selected_project_id)


@app.route('/suites/create', methods=['POST'])
def create_suite():
    init_client()
    project_id = request.form.get('project_id', type=int)
    project_prefix = request.form.get('project_prefix', '').strip()
    parent_suite_id = request.form.get('parent_suite_id', type=int) or None
    suite_name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    if not project_id or not suite_name:
        flash("Project and Suite Name are required", "error")
        return redirect(url_for('suites'))

    try:
        result = client.create_suite(project_prefix, suite_name, description, parent_suite_id)
        if result and not (isinstance(result, list) and result and 'code' in result[0]):
            flash(f"Test Suite '{suite_name}' created successfully", "success")
        else:
            err_msg = result[0]['message'] if isinstance(result, list) and result else "Failed to create test suite"
            flash(f"Failed to create test suite: {err_msg}", "error")
    except Exception as e:
        flash(f"Error creating suite: {str(e)}", "error")

    return redirect(url_for('suites') + f"?project_id={project_id}")


@app.route('/testcases')
def testcases():
    init_client()
    projects_list = []
    suites_list = []
    plans_list = []
    testcases_list = []
    requirements_list = []
    req_specs = []
    selected_project_id = request.args.get('project_id', type=int)
    selected_suite_id = request.args.get('suite_id', type=int)

    try:
        projects_list = client.get_projects()
        if selected_project_id:
            suites_list = client.get_suites(selected_project_id)
            plans_list = client.get_plans(selected_project_id)
            req_specs = client.get_req_specs(selected_project_id)
            for spec in req_specs:
                reqs = client.get_requirements_in_spec(spec['id'])
                for r in reqs:
                    r['spec_id'] = spec['id']
                    r['spec_name'] = spec.get('name', spec.get('doc_id', ''))
                requirements_list.extend(reqs)
        else:
            selected_project_id = projects_list[0]['id'] if projects_list else None
            if selected_project_id:
                suites_list = client.get_suites(selected_project_id)
                plans_list = client.get_plans(selected_project_id)
                req_specs = client.get_req_specs(selected_project_id)
                for spec in req_specs:
                    reqs = client.get_requirements_in_spec(spec['id'])
                    for r in reqs:
                        r['spec_id'] = spec['id']
                        r['spec_name'] = spec.get('name', spec.get('doc_id', ''))
                    requirements_list.extend(reqs)
        if selected_suite_id:
            testcases_list = client.get_testcases_in_suite(selected_suite_id)
        elif selected_project_id:
            testcases_list = client.get_testcases_in_project(selected_project_id)
    except Exception as e:
        flash(f"Error fetching test cases: {str(e)}", "error")

    return render_template('testcases.html',
                         projects=projects_list,
                         suites=suites_list,
                         plans=plans_list,
                         testcases=testcases_list,
                         requirements=requirements_list,
                         req_specs=req_specs,
                         selected_project_id=selected_project_id,
                         selected_suite_id=selected_suite_id)


@app.route('/assign-tc-to-spec', methods=['POST'])
def assign_testcases_to_spec():
    init_client()
    spec_id = request.form.get('spec_id', type=int)
    tc_ids_raw = request.form.getlist('testcase_ids')
    project_id = request.form.get('project_id', type=int)

    tc_ids = [int(x) for x in tc_ids_raw if str(x).isdigit()]

    if not spec_id:
        flash("Requirement Specification is required", "error")
        return redirect(url_for('testcases', project_id=project_id))
    if not tc_ids:
        flash("No test cases selected", "error")
        return redirect(url_for('testcases', project_id=project_id))

    try:
        reqs = client.get_requirements_in_spec(spec_id)
        if not reqs:
            flash("No requirements found in this specification. Create one first.", "error")
            return redirect(url_for('testcases', project_id=project_id))

        total_assigned = 0
        total_skipped = 0
        for req in reqs:
            result = client.assign_testcases_to_req(req['id'], tc_ids)
            total_assigned += result.get('assigned', 0)
            total_skipped += result.get('skipped', 0)

        flash(
            f"Assigned {total_assigned} test case(s) across {len(reqs)} requirement(s); "
            f"skipped {total_skipped} already linked.",
            "success"
        )
    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    return redirect(url_for('testcases', project_id=project_id))


@app.route('/testcases/create', methods=['POST'])
def create_testcase():
    init_client()
    suite_id = request.form.get('suite_id', type=int)
    name = request.form.get('name', '').strip()
    summary = request.form.get('summary', '').strip()
    expected_results = request.form.get('expected_results', '').strip()
    keywords_str = request.form.get('keywords', '').strip()
    redirect_project_id = request.form.get('redirect_project_id', type=int)
    plan_id = request.form.get('plan_id', type=int) or None
    
    steps_actions = request.form.getlist('step_actions')
    step_results = request.form.getlist('step_results')
    
    if not suite_id or not name:
        flash("Suite and Test Case Name are required", "error")
        return redirect(url_for('testcases'))
    
    steps = []
    for i, action in enumerate(steps_actions):
        if action.strip():
            steps.append({
                'actions': action.strip(),
                'expected_results': step_results[i].strip() if i < len(step_results) else expected_results
            })
    
    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
    
    try:
        result = client.create_testcase(
            suite_id=suite_id,
            project_id=redirect_project_id,
            name=name,
            summary=summary,
            steps=steps,
            expected_results=[expected_results] * len(steps) if steps else [expected_results],
            author_login=client.get_current_user()
        )
        
        if result:
            flash(f"Test Case '{name}' created successfully", "success")
            
            if plan_id and 'external_id' in result:
                try:
                    client.add_case_to_plan(plan_id, result['external_id'])
                    flash("Test Case added to test plan", "success")
                except:
                    pass
        else:
            flash("Failed to create test case", "error")
    except Exception as e:
        flash(f"Error creating test case: {str(e)}", "error")

    return redirect(url_for('testcases', project_id=redirect_project_id, suite_id=suite_id))


@app.route('/testcases/bulk', methods=['POST'])
def create_testcases_bulk():
    init_client()
    project_id = request.form.get('project_id', type=int)
    suite_id = request.form.get('suite_id', type=int)
    raw = request.form.get('json_data', '').strip()

    if not suite_id:
        flash("Suite is required", "error")
        return redirect(url_for('testcases', project_id=project_id))
    if not raw:
        flash("JSON is empty", "error")
        return redirect(url_for('testcases', project_id=project_id, suite_id=suite_id))

    try:
        items = json.loads(raw)
    except Exception as e:
        flash(f"Invalid JSON: {e}", "error")
        return redirect(url_for('testcases', project_id=project_id, suite_id=suite_id))

    if not isinstance(items, list):
        flash("JSON must be a list of test cases", "error")
        return redirect(url_for('testcases', project_id=project_id, suite_id=suite_id))

    success, failed = 0, 0
    error_msgs = []
    for item in items:
        if not isinstance(item, dict):
            failed += 1
            continue
        name = (item.get('name') or '').strip()
        if not name:
            failed += 1
            continue
        summary = item.get('summary') or ''
        steps_in = item.get('steps') or []
        if not isinstance(steps_in, list):
            steps_in = []
        steps = []
        expected = item.get('expected') or []
        if not isinstance(expected, list):
            expected = []
        for s in steps_in:
            if isinstance(s, dict):
                steps.append(s.get('actions') or s.get('step') or '')
                expected.append(s.get('expected_results') or s.get('expected') or '')
            else:
                steps.append(str(s))
                expected.append('')
        if not steps:
            steps = ['']
            expected = ['']
        try:
            client.create_testcase_with_check(
                suite_id=suite_id, name=name, summary=summary,
                steps=steps, expected_results=expected, project_id=project_id
            )
            success += 1
        except Exception as e:
            failed += 1
            error_msgs.append(f"{name}: {e}")

    msg = f"Bulk create done: {success} created, {failed} failed"
    if error_msgs:
        msg += " | " + " | ".join(error_msgs[:5])
    flash(msg, "success" if failed == 0 else "error")
    return redirect(url_for('testcases', project_id=project_id, suite_id=suite_id))


@app.route('/testcases/<int:tc_id>')
def testcase_detail(tc_id):
    init_client()
    testcase = None
    error = None
    try:
        testcase = client.get_testcase_by_id(tc_id)
    except Exception as e:
        error = str(e)
    return render_template('testcase_detail.html', testcase=testcase, error=error)


@app.route('/testcases/<int:tc_id>/delete', methods=['POST'])
def delete_testcase(tc_id):
    init_client()
    project_id = request.form.get('project_id', type=int)
    suite_id = request.form.get('suite_id', type=int)

    try:
        tc_info = client.get_testcase_info(tc_id)
        if not tc_info:
            flash("Test case not found", "error")
            return redirect(url_for('testcases', project_id=project_id, suite_id=suite_id))

        if client.has_executions(tc_id):
            flash("Cannot delete test case that has execution history", "error")
            return redirect(url_for('testcases', project_id=project_id, suite_id=suite_id))

        if client.delete_testcase(tc_id):
            flash(f"Test case '{tc_info.get('name', tc_id)}' deleted successfully", "success")
        else:
            flash("Failed to delete test case", "error")
    except Exception as e:
        flash(f"Error deleting test case: {str(e)}", "error")

    return redirect(url_for('testcases', project_id=project_id, suite_id=suite_id))


@app.route('/executions')
def executions():
    init_client()
    projects_list = []
    plans_list = []
    builds_list = []
    testcases_list = []
    executions_list = []
    
    selected_project_id = request.args.get('project_id', type=int)
    selected_plan_id = request.args.get('plan_id', type=int)
    selected_build_id = request.args.get('build_id', type=int)
    
    try:
        projects_list = client.get_projects()
        
        if selected_project_id:
            plans_list = client.get_plans(selected_project_id)
        
        if selected_plan_id:
            builds_list = client.get_builds(selected_plan_id)
            testcases_list = client.get_cases_for_plan(selected_plan_id)
            executions_list = client.get_executions(selected_plan_id, selected_build_id)
        
    except Exception as e:
        flash(f"Error loading executions: {str(e)}", "error")
    
    return render_template('executions.html',
                         projects=projects_list,
                         plans=plans_list,
                         builds=builds_list,
                         testcases=testcases_list,
                         executions=executions_list,
                         selected_project_id=selected_project_id,
                         selected_plan_id=selected_plan_id,
                         selected_build_id=selected_build_id)


@app.route('/executions/build', methods=['POST'])
def create_build():
    init_client()
    plan_id = request.form.get('plan_id', type=int)
    build_name = request.form.get('build_name', '').strip()
    notes = request.form.get('notes', '').strip()
    project_id = request.form.get('project_id', type=int)

    try:
        if not plan_id or not build_name:
            flash("Plan and build name are required.", "error")
        else:
            client.create_build(plan_id, build_name, notes)
            flash(f"Build '{build_name}' created successfully.", "success")
    except Exception as e:
        flash(f"Error creating build: {str(e)}", "error")

    params = f"project_id={project_id}&plan_id={plan_id}"
    return redirect(f"{url_for('executions')}?{params}")


@app.route('/executions/result', methods=['POST'])
def report_result():
    init_client()
    plan_id = request.form.get('plan_id', type=int)
    build_id = request.form.get('build_id', type=int)
    case_external_id = request.form.get('case_external_id', '').strip()
    status = request.form.get('status', '').strip()
    notes = request.form.get('notes', '').strip()
    tester_id = request.form.get('tester_id', type=int) or None
    
    if not all([plan_id, build_id, case_external_id, status]):
        flash("Plan, Build, Test Case, and Status are required", "error")
    else:
        try:
            result = client.report_result(plan_id, build_id, case_external_id, status, notes, tester_id)
            # Success if result is not None and not an error dict
            if result is not None and not (isinstance(result, dict) and result.get('code')):
                flash("Test result reported successfully", "success")
            else:
                err_msg = result.get('message', '') if isinstance(result, dict) else str(result)
                flash(f"Failed to report test result: {err_msg}", "error")
        except Exception as e:
            flash(f"Error reporting result: {str(e)}", "error")
    
    # Preserve URL params when redirecting
    params = f"project_id={request.form.get('project_id', '')}&plan_id={plan_id}&build_id={build_id}"
    return redirect(f"{url_for('executions')}?{params}")


@app.route('/executions/save_all', methods=['POST'])
def save_all_results():
    init_client()
    plan_id = request.form.get('plan_id', type=int)
    build_id = request.form.get('build_id', type=int)
    project_id = request.form.get('project_id', type=int)
    
    if not plan_id or not build_id:
        flash("Plan and Build are required", "error")
        return redirect(url_for('executions'))
    
    saved_count = 0
    failed_count = 0
    
    # Get all form data and find test case entries
    for key in request.form:
        if key.startswith('status_'):
            case_external_id = key.replace('status_', '')
            status = request.form.get(key, 'n').strip()
            notes = request.form.get(f'notes_{case_external_id}', '').strip()
            
            try:
                result = client.report_result(plan_id, build_id, case_external_id, status, notes)
                if result is not None and not (isinstance(result, dict) and result.get('code')):
                    saved_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"Error saving result for {case_external_id}: {e}")
                failed_count += 1
    
    if saved_count > 0:
        flash(f"Saved {saved_count} test results successfully", "success")
    if failed_count > 0:
        flash(f"Failed to save {failed_count} results", "error")
    if saved_count == 0 and failed_count == 0:
        flash("No test results to save", "warning")
    
    params = f"project_id={project_id}&plan_id={plan_id}&build_id={build_id}"
    return redirect(f"{url_for('executions')}?{params}")


@app.route('/export')
def export():
    init_client()
    projects_list = []
    plans_list = []
    builds_list = []
    
    selected_project_id = request.args.get('project_id', type=int)
    selected_plan_id = request.args.get('plan_id', type=int)
    selected_build_id = request.args.get('build_id', type=int)
    
    try:
        projects_list = client.get_projects()
        
        if selected_project_id:
            plans_list = client.get_plans(selected_project_id)
        
        if selected_plan_id:
            builds_list = client.get_builds(selected_plan_id)
    except Exception as e:
        flash(f"Error loading export options: {str(e)}", "error")
    
    return render_template('export.html',
                         projects=projects_list,
                         plans=plans_list,
                         builds=builds_list,
                         selected_project_id=selected_project_id,
                         selected_plan_id=selected_plan_id,
                         selected_build_id=selected_build_id)


@app.route('/export/word', methods=['POST'])
def export_word():
    init_client()
    plan_id = request.form.get('plan_id', type=int)
    build_id = request.form.get('build_id', type=int) or None
    
    if not plan_id:
        flash("Test Plan is required", "error")
        return redirect(url_for('export'))
    
    try:
        client.connect_db()
        generator = ReportGenerator(client)
        output_path = generator.generate_report(plan_id, build_id)
        
        return send_file(output_path, 
                        as_attachment=True,
                        download_name=os.path.basename(output_path))
    except Exception as e:
        flash(f"Error generating report: {str(e)}", "error")
        return redirect(url_for('export'))


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        api_key = request.form.get('api_key', '').strip()
        if api_key:
            session['api_key'] = api_key
            if client.connect(api_key):
                flash("API key saved and connection successful", "success")
            else:
                flash("API key saved but connection failed", "warning")
        return redirect(url_for('dashboard'))

    api_key = session.get('api_key', '')

    # Auto-fill from DB if not set
    if not api_key:
        try:
            import mysql.connector
            from config import DB_HOST, DB_USER, DB_PASS, DB_NAME
            conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
            cur = conn.cursor()
            cur.execute("SELECT script_key FROM users WHERE active=1 AND script_key IS NOT NULL LIMIT 1")
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row and row[0]:
                api_key = row[0]
        except Exception:
            pass

    return render_template('settings.html', api_key=api_key)


@app.route('/requirements/spec/<int:spec_id>')
def req_spec_detail(spec_id):
    init_client()
    projects_list = []
    spec_detail = {}
    requirements_list = []
    testcases_for_assign = []
    selected_project_id = None
    try:
        spec_detail = client.get_req_spec_detail(spec_id)
        if spec_detail:
            selected_project_id = spec_detail.get('testproject_id')
            projects_list = client.get_projects()
            requirements_list = client.get_requirements_with_coverage(spec_id)
            testcases_for_assign = client.get_testcases_for_assign(selected_project_id)
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return render_template('req_spec_detail.html',
                         spec=spec_detail,
                         requirements=requirements_list,
                         testcases=testcases_for_assign,
                         projects=projects_list,
                         selected_project_id=selected_project_id)

@app.route('/requirements/spec/<int:spec_id>/edit', methods=['GET', 'POST'])
def edit_req_spec(spec_id):
    init_client()
    if request.method == 'POST':
        doc_id = request.form.get('doc_id', '').strip()
        title = request.form.get('title', '').strip()
        scope = request.form.get('scope', '').strip()
        spec_type = request.form.get('spec_type', 'N').strip()
        project_id = request.form.get('project_id', type=int)
        try:
            result = client.update_req_spec(spec_id, doc_id, title, scope, spec_type)
            if result.get('status_ok'):
                flash(f"Spec '{title}' updated.", "success")
            else:
                flash(f"Failed: {result.get('msg')}", "error")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
        return redirect(url_for('req_spec_detail', spec_id=spec_id))
    spec_detail = client.get_req_spec_detail(spec_id)
    return render_template('edit_req_spec.html', spec=spec_detail)

@app.route('/requirements/spec/<int:spec_id>/delete', methods=['POST'])
def delete_req_spec_route(spec_id):
    init_client()
    project_id = request.form.get('project_id', type=int)
    try:
        result = client.delete_req_spec(spec_id)
        if result.get('status_ok'):
            flash("Requirement Specification deleted.", "success")
        else:
            flash(f"Failed: {result.get('msg')}", "error")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect(url_for('requirements', project_id=project_id))

@app.route('/requirements/req/<int:req_id>/delete', methods=['POST'])
def delete_requirement(req_id):
    init_client()
    spec_id = request.form.get('spec_id', type=int)
    project_id = request.form.get('project_id', type=int)
    try:
        cursor = client.db_connection.cursor()
        # Get version id via nodes_hierarchy type=8
        cursor.execute(
            "SELECT id FROM nodes_hierarchy WHERE parent_id = %s AND node_type_id = 8 ORDER BY id DESC LIMIT 1",
            (req_id,)
        )
        ver_row = cursor.fetchone()
        if ver_row:
            ver_id = ver_row[0]
            cursor.execute("DELETE FROM req_coverage WHERE req_id = %s", (req_id,))
            cursor.execute("DELETE FROM req_versions WHERE id = %s", (ver_id,))
        cursor.execute("DELETE FROM requirements WHERE id = %s", (req_id,))
        cursor.execute("DELETE FROM nodes_hierarchy WHERE id = %s OR parent_id = %s", (req_id, req_id))
        client.db_connection.commit()
        cursor.close()
        flash("Requirement deleted.", "success")
    except Exception as e:
        client.db_connection.rollback()
        flash(f"Error: {str(e)}", "error")
    return redirect(url_for('req_spec_detail', spec_id=spec_id))

@app.route('/assign-tc-to-req', methods=['POST'])
def assign_tc_to_req_route():
    init_client()
    tc_ids = request.form.getlist('testcase_ids')
    req_ids = request.form.getlist('req_ids')
    project_id = request.form.get('project_id', type=int)

    if not tc_ids or not req_ids:
        flash("No test cases or requirements selected.", "error")
        return redirect(url_for('testcases', project_id=project_id))

    success_count = 0
    try:
        for req_id in req_ids:
            result = client.assign_testcases_to_req(int(req_id), [int(t) for t in tc_ids])
            if result.get('status_ok'):
                success_count += 1
        flash(f"Assigned test case(s) to requirement(s).", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    return redirect(url_for('testcases', project_id=project_id))

@app.route('/requirements')
def requirements():
    init_client()
    projects_list = []
    req_specs_list = []
    requirements_list = []
    selected_project_id = request.args.get('project_id', type=int)
    selected_spec_id = request.args.get('spec_id', type=int)

    try:
        projects_list = client.get_projects()
        if selected_project_id:
            req_specs_list = client.get_req_specs(selected_project_id)
        if selected_spec_id:
            requirements_list = client.get_requirements_in_spec(selected_spec_id)
    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    return render_template('requirements.html',
                         projects=projects_list,
                         req_specs=req_specs_list,
                         requirements=requirements_list,
                         selected_project_id=selected_project_id,
                         selected_spec_id=selected_spec_id)


@app.route('/requirements/create/spec', methods=['POST'])
def create_req_spec():
    init_client()
    project_id = request.form.get('project_id', type=int)
    doc_id = request.form.get('doc_id', '').strip()
    title = request.form.get('title', '').strip()
    scope = request.form.get('scope', '').strip()
    spec_type = request.form.get('spec_type', 'N').strip() or 'N'

    if not project_id:
        flash("Project is required", "error")
        return redirect(url_for('requirements'))
    if not doc_id:
        flash("Doc ID is required", "error")
        return redirect(url_for('requirements', project_id=project_id))
    if not title:
        flash("Title is required", "error")
        return redirect(url_for('requirements', project_id=project_id))

    try:
        result = client.create_req_spec(project_id, doc_id, title,
                                        scope=scope, spec_type=spec_type)
        if result.get('status_ok'):
            flash(f"Req Spec '{title}' created (ID: {result['id']})", "success")
        else:
            flash(f"Failed: {result.get('msg', 'Unknown error')}", "error")
    except Exception as e:
        flash(f"Error creating req spec: {str(e)}", "error")

    return redirect(url_for('requirements', project_id=project_id))


@app.route('/requirements/create/req', methods=['POST'])
def create_requirement():
    init_client()
    spec_id = request.form.get('spec_id', type=int)
    project_id = request.form.get('project_id', type=int)
    req_doc_id = request.form.get('req_doc_id', '').strip()
    title = request.form.get('title', '').strip()
    scope = request.form.get('scope', '').strip()
    status = request.form.get('status', 'V').strip()
    req_type = request.form.get('req_type', 'I').strip()
    coverage = request.form.get('expected_coverage', 1, type=int)

    if not spec_id:
        flash("Req Spec is required", "error")
        return redirect(url_for('requirements', project_id=project_id))
    if not req_doc_id:
        flash("Req Doc ID is required", "error")
        return redirect(url_for('requirements', project_id=project_id, spec_id=spec_id))
    if not title:
        flash("Title is required", "error")
        return redirect(url_for('requirements', project_id=project_id, spec_id=spec_id))

    try:
        result = client.create_requirement(
            spec_id, req_doc_id, title,
            scope=scope, status=status, req_type=req_type,
            expected_coverage=coverage
        )
        if result.get('status_ok'):
            flash(f"Requirement '{title}' created (ID: {result['id']})", "success")
        else:
            flash(f"Failed: {result.get('msg', 'Unknown error')}", "error")
    except Exception as e:
        flash(f"Error creating requirement: {str(e)}", "error")

    return redirect(url_for('requirements', project_id=project_id, spec_id=spec_id))


if __name__ == '__main__':
    print(f"Starting TestLink Tool at http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=True)
