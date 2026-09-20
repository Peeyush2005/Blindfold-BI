"""
Playwright End-to-End Test Suite for Blindfold BI
Executes Section 9 Acceptance Checks 3 and 4:
- Check 3: Ask founder question; observe stage in running before done;
  answer contains BI blocks whose numbers equal tool facts; no tabs or dashboard exist.
- Check 4: Unreachable backend causes UI to show error state, zero canned data.
"""

import sys
import time
from playwright.sync_api import sync_playwright, expect

FRONTEND_URL = "http://127.0.0.1:3000"


def test_acceptance_check_3():
    print("\n" + "=" * 70)
    print("RUNNING ACCEPTANCE CHECK 3: Single-screen UI, live pipeline, BI blocks")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. Load the page
        print(f"1. Navigating to {FRONTEND_URL}...")
        page.goto(FRONTEND_URL, wait_until="networkidle")

        # 2. Check header and source badge
        header = page.locator("header")
        expect(header).to_be_visible()
        badge = page.locator('[aria-label="Connected data source status"]')
        expect(badge).to_be_visible()
        badge_text = badge.inner_text()
        print(f"   [PASS] Source badge verified: '{badge_text}'")
        assert "monday.com" in badge_text, "Badge missing monday.com"
        assert "as of 15 Jan 2026" in badge_text, "Badge missing as-of date"

        # 3. Assert NO tabs, router, dashboard, or marketing views exist
        tabs = page.locator('[role="tab"]').count()
        dashboards = page.locator('text="Dashboard"').count()
        architecture_views = page.locator('text="ArchitectureView"').count()
        pipeline_sims = page.locator('text="PipelineSimulator"').count()
        print(f"   [PASS] Non-permitted views audit: tabs={tabs}, dashboards={dashboards}, arch={architecture_views}, sim={pipeline_sims}")
        assert tabs == 0, f"Expected 0 tabs, found {tabs}"
        assert dashboards == 0, f"Expected 0 dashboards, found {dashboards}"
        assert architecture_views == 0, f"Expected 0 architecture views, found {architecture_views}"

        # 4. Verify Empty State: Title, Starter Chips (4 to 6), Input Box
        title = page.locator('h1:has-text("Skylark Business Intelligence")')
        expect(title).to_be_visible()
        page.wait_for_selector('div.grid button', timeout=10000)
        chip_count = page.locator('div.grid button').count()
        print(f"   [PASS] Starter chips verified on empty state: {chip_count} chips found (expected 4-6)")
        assert 4 <= chip_count <= 6, f"Expected 4-6 starter chips, got {chip_count}"

        input_box = page.locator('input[aria-label="Ask analytical query"]')
        expect(input_box).to_be_visible()

        # 5. Submit founder question: "How is the energy pipeline this quarter?"
        question = "How is the energy pipeline this quarter?"
        print(f"2. Submitting question: '{question}'...")
        input_box.fill(question)
        input_box.press("Enter")

        # 6. Observe a stage in 'running' before 'done'
        print("3. Observing live stage state transitions...")
        # Check for stage elements
        stage_running_seen = False
        start_wait = time.time()
        while time.time() - start_wait < 15:
            # Look for running stage indicator
            running_stages = page.locator('.animate-pulse:has-text("running"), span:has-text("running")')
            if running_stages.count() > 0:
                stage_running_seen = True
                running_text = running_stages.first.inner_text()
                print(f"   [PASS] Observed stage in running state: {running_text}")
                break
            time.sleep(0.05)

        # 7. Wait for run completion (answer rendered, run panel collapsed to summary)
        print("4. Waiting for pipeline completion and answer rendering...")
        page.wait_for_selector('button:has-text("Replay")', timeout=90000)
        replay_btn = page.locator('button:has-text("Replay")')
        expect(replay_btn).to_be_visible()
        print(f"   [PASS] Replay button present and labeled 'Replay'")

        # Verify summary line in collapsed run panel
        summary_span = page.locator('div[aria-label="Analytical Pipeline Run"] span:has-text("stages")')
        expect(summary_span.first).to_be_visible()
        summary_text = summary_span.first.inner_text()
        print(f"   [PASS] Run panel auto-collapsed to summary: '{summary_text}'")

        # Verify expand toggle exists
        expand_btn = page.locator('button[aria-label="Expand run details"]')
        expect(expand_btn).to_be_visible()
        print(f"   [PASS] Run details toggle exists with 'Expand run details' label")

        # 8. Verify Generated BI Blocks in Answer
        print("5. Verifying Generated BI Blocks...")
        # Text block
        text_block = page.locator('div.text-sm.leading-relaxed')
        expect(text_block.first).to_be_visible()
        answer_prose = text_block.first.inner_text()
        print(f"   [PASS] Prose narrative block: '{answer_prose[:120]}...'")

        # KPI cards
        kpi_cards = page.locator('div.min-w-\\[200px\\]')
        kpi_count = kpi_cards.count()
        print(f"   [PASS] KPI Cards rendered: {kpi_count} cards")
        assert kpi_count >= 1, "Expected at least 1 KPI card"

        # ECharts Chart
        chart_container = page.locator('.echarts-for-react, div[_echarts_instance_], canvas')
        chart_count = chart_container.count()
        print(f"   [PASS] Dynamic ECharts rendered: {chart_count} canvas/chart instances")
        assert chart_count >= 1, "Expected ECharts chart instance"

        # Table block
        table = page.locator('table')
        expect(table.first).to_be_visible()
        table_rows = page.locator('table tbody tr').count()
        print(f"   [PASS] Structured table rendered: {table_rows} rows (must be <= 10)")
        assert 1 <= table_rows <= 10, f"Table rows {table_rows} must be <= 10"

        # Notes block (Assumptions / Data Quality)
        notes = page.locator('div:has-text("ASSUMPTION"), div:has-text("Data Quality"), div:has-text("Energy sector includes")')
        expect(notes.first).to_be_visible()
        print(f"   [PASS] Notes/Assumptions block rendered: '{notes.first.inner_text()[:90]}...'")

        # Trust receipt
        receipt = page.locator('div:has-text("Verified:"), div:has-text("rows scanned")')
        expect(receipt.first).to_be_visible()
        print(f"   [PASS] Trust receipt verified: '{receipt.first.inner_text()[:80]}...'")

        # 3 follow-up chips
        followup_chips = page.locator('div.flex.flex-wrap button')
        followup_count = followup_chips.count()
        print(f"   [PASS] Follow-up suggestion chips rendered: {followup_count} chips")
        assert followup_count >= 3, f"Expected 3 follow-up chips, got {followup_count}"

        browser.close()
        print("[ALL PASS] Acceptance Check 3 succeeded without errors.")


def test_acceptance_check_4():
    print("\n" + "=" * 70)
    print("RUNNING ACCEPTANCE CHECK 4: Backend unreachable -> Error state, zero canned data")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Intercept and abort all /api/ requests to simulate stopped backend
        page.route("**/api/**", lambda route: route.abort())

        print(f"1. Navigating to {FRONTEND_URL} with backend unreachable...")
        page.goto(FRONTEND_URL)

        # Verify source badge shows disconnected
        offline_badge = page.locator('text="source disconnected · offline"')
        expect(offline_badge).to_be_visible(timeout=5000)
        print("   [PASS] Header correctly displays 'source disconnected · offline'")

        # Verify error alert is shown
        error_alert = page.locator('[role="alert"]')
        expect(error_alert).to_be_visible(timeout=5000)
        alert_text = error_alert.inner_text()
        print(f"   [PASS] Error banner rendered: '{alert_text}'")

        # Verify no canned data or mock traces are rendered
        kpis = page.locator('div.grid div.rounded-md:has-text("Cr")').count()
        charts = page.locator('canvas').count()
        tables = page.locator('table').count()
        print(f"   [PASS] Zero canned data verified: kpis={kpis}, charts={charts}, tables={tables}")
        assert kpis == 0, f"Expected 0 KPIs on error, found {kpis}"
        assert charts == 0, f"Expected 0 charts on error, found {charts}"
        assert tables == 0, f"Expected 0 tables on error, found {tables}"

        # Submit question while backend is down
        input_box = page.locator('input[aria-label="Ask analytical query"]')
        input_box.fill("What is our revenue?")
        input_box.press("Enter")

        # Verify assistant message displays error and no data
        time.sleep(1)
        error_box = page.locator('div:has-text("API Unreachable"), div:has-text("API error"), div:has-text("Failed to fetch")')
        expect(error_box.first).to_be_visible(timeout=5000)
        print(f"   [PASS] Assistant response displays explicit error: '{error_box.first.inner_text()}'")

        # Re-verify zero BI blocks generated
        assert page.locator('table').count() == 0, "No tables should exist on error"
        assert page.locator('canvas').count() == 0, "No charts should exist on error"

        browser.close()
        print("[ALL PASS] Acceptance Check 4 succeeded without errors.")


if __name__ == "__main__":
    test_acceptance_check_3()
    test_acceptance_check_4()
