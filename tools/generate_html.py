#!/usr/bin/env python3
"""
tools/generate_html.py

WP-G & WP-C: Newsletter HTML Compiler.
Compiles synthesized JSON payload into clean, responsive HTML email.
Renders ONLY sections present in the payload.
"""

import os
import sys
import json
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".tmp")
INPUT_FILE = os.path.join(TMP_DIR, "synthesized_news.json")
OUTPUT_FILE = os.path.join(TMP_DIR, "newsletter.html")


def generate_html():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} does not exist.")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    launches = data.get("launches", [])
    business = data.get("business", [])
    crisis = data.get("crisis", [])
    headtohead = data.get("headtohead", [])
    repo_radar = data.get("repo_radar", [])

    total_items = (
        len(launches) + len(business) + len(crisis) + len(headtohead) + len(repo_radar)
    )

    current_date = datetime.now(timezone.utc).strftime("%B %d, %Y")

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BUILDR.ai — Daily Technical Briefing</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #0F172A;
            background-color: #F8FAFC;
            margin: 0;
            padding: 0;
            -webkit-font-smoothing: antialiased;
        }}
        .content {{
            max-width: 650px;
            margin: 0 auto;
            background: #ffffff;
        }}
    </style>
</head>
<body style="background-color: #F8FAFC; margin: 0; padding: 20px 0;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #F8FAFC;">
        <tr>
            <td align="center">
                <table class="content" width="650" cellpadding="0" cellspacing="0" border="0" style="max-width: 650px; width: 650px; background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0; overflow: hidden;">
                    <!-- HEADER -->
                    <tr>
                        <td style="padding: 40px 32px 24px 32px; border-bottom: 1px solid #F1F5F9; background-color: #FFFFFF;">
                            <a href="#" style="font-size: 26px; font-weight: 800; color: #0F172A; letter-spacing: -0.04em; text-decoration: none; display: inline-block;">BUILDR<span style="color: #7C3AED;">.ai</span></a>
                            <p style="margin: 6px 0 0 0; font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.15em; text-transform: uppercase;">AI AUTOMATION & SOLUTIONS BRIEF &bull; {current_date}</p>
                        </td>
                    </tr>
                    
                    <!-- MAIN BODY -->
                    <tr>
                        <td style="padding: 32px;">
    """

    if total_items == 0:
        html_content += """
                            <div style="text-align: center; padding: 48px 0;">
                                <p style="font-size: 15px; color: #94A3B8; font-weight: 500;">No briefing compiles available for this cycle.</p>
                            </div>
        """
    else:
        # SECTION 1: LAUNCHES & AI TOOLS
        if launches:
            html_content += """
                            <!-- SECTION HEADER: LAUNCHES -->
                            <div style="margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #7C3AED;">
                                <h3 style="margin: 0; font-size: 14px; font-weight: 800; color: #7C3AED; letter-spacing: 0.1em; text-transform: uppercase;">01 // LAUNCHES & AI TOOLS</h3>
                            </div>
            """
            for item in launches:
                html_content += f"""
                            <div style="padding-bottom: 24px; margin-bottom: 24px; border-bottom: 1px solid #F1F5F9;">
                                <h2 style="font-size: 17px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0;">
                                    <a href="{item.get('url', '#')}" target="_blank" style="color: #0F172A; text-decoration: none;">{item.get('title')}</a>
                                </h2>
                                <p style="font-size: 14px; color: #475569; margin: 0 0 10px 0;">{item.get('what_it_is', '')}</p>
                                <div style="background-color: #F3E8FF; border-left: 3px solid #7C3AED; padding: 10px 14px; font-size: 13px; color: #581C87;">
                                    <strong>Automation Use Case:</strong> {item.get('automation_use_case', item.get('why_it_matters', ''))}
                                </div>
                            </div>
                """

        # SECTION 2: BUSINESS AI IN ACTION
        if business:
            html_content += """
                            <!-- SECTION HEADER: BUSINESS AI IN ACTION -->
                            <div style="margin-top: 16px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #059669;">
                                <h3 style="margin: 0; font-size: 14px; font-weight: 800; color: #059669; letter-spacing: 0.1em; text-transform: uppercase;">02 // BUSINESS AI IN ACTION & INDUSTRY SOLUTIONS</h3>
                            </div>
            """
            for item in business:
                html_content += f"""
                            <div style="padding-bottom: 24px; margin-bottom: 24px; border-bottom: 1px solid #F1F5F9;">
                                <h2 style="font-size: 17px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0;">
                                    <a href="{item.get('url', '#')}" target="_blank" style="color: #0F172A; text-decoration: none;">{item.get('title')}</a>
                                </h2>
                                <p style="font-size: 14px; color: #475569; margin: 0 0 10px 0;"><strong>What They Did:</strong> {item.get('what_they_did', '')}</p>
                                <div style="background-color: #ECFDF5; border-left: 3px solid #059669; padding: 10px 14px; font-size: 13px; color: #065F46;">
                                    <strong>Client Solution Opportunity:</strong> {item.get('solution_opportunity', '')}
                                </div>
                            </div>
                """

        # SECTION 3: CRISIS WATCH
        if crisis:
            html_content += """
                            <!-- SECTION HEADER: CRISIS WATCH -->
                            <div style="margin-top: 16px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #DC2626;">
                                <h3 style="margin: 0; font-size: 14px; font-weight: 800; color: #DC2626; letter-spacing: 0.1em; text-transform: uppercase;">03 // AI CRISIS WATCH & INCIDENTS</h3>
                            </div>
            """
            for item in crisis:
                html_content += f"""
                            <div style="padding-bottom: 24px; margin-bottom: 24px; border-bottom: 1px solid #F1F5F9;">
                                <h2 style="font-size: 17px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0;">
                                    <a href="{item.get('url', '#')}" target="_blank" style="color: #0F172A; text-decoration: none;">{item.get('title')}</a>
                                </h2>
                                <p style="font-size: 14px; color: #475569; margin: 0 0 10px 0;">{item.get('crisis_summary', '')}</p>
                                <div style="background-color: #FEF2F2; border-left: 3px solid #DC2626; padding: 10px 14px; font-size: 13px; color: #991B1B;">
                                    <strong>Automation Fix:</strong> {item.get('automation_fix', '')}
                                </div>
                            </div>
                """

        # SECTION 4: HEAD TO HEAD
        if headtohead:
            html_content += """
                            <!-- SECTION HEADER: HEAD TO HEAD -->
                            <div style="margin-top: 16px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #D97706;">
                                <h3 style="margin: 0; font-size: 14px; font-weight: 800; color: #D97706; letter-spacing: 0.1em; text-transform: uppercase;">04 // HEAD TO HEAD BENCHMARKS</h3>
                            </div>
            """
            for item in headtohead:
                html_content += f"""
                            <div style="padding-bottom: 24px; margin-bottom: 24px; border-bottom: 1px solid #F1F5F9;">
                                <h2 style="font-size: 17px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0;">
                                    <a href="{item.get('url', '#')}" target="_blank" style="color: #0F172A; text-decoration: none;">{item.get('title')}</a>
                                </h2>
                                <p style="font-size: 14px; color: #475569; margin: 0 0 10px 0;"><strong>Verdict:</strong> {item.get('verdict', '')}</p>
                                <div style="background-color: #FFFBEB; border-left: 3px solid #D97706; padding: 10px 14px; font-size: 13px; color: #92400E;">
                                    <strong>Use When:</strong> {item.get('use_when', '')}
                                </div>
                            </div>
                """

        # SECTION 5: REPO RADAR
        if repo_radar:
            html_content += """
                            <!-- SECTION HEADER: REPO RADAR -->
                            <div style="margin-top: 16px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #0284C7;">
                                <h3 style="margin: 0; font-size: 14px; font-weight: 800; color: #0284C7; letter-spacing: 0.1em; text-transform: uppercase;">05 // REPO RADAR</h3>
                            </div>
            """
            for item in repo_radar:
                html_content += f"""
                            <div style="padding-bottom: 24px; margin-bottom: 24px; border-bottom: 1px solid #F1F5F9;">
                                <h2 style="font-size: 17px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0;">
                                    <a href="{item.get('html_url', item.get('url', '#'))}" target="_blank" style="color: #0F172A; text-decoration: none;">{item.get('full_name', item.get('title'))}</a>
                                </h2>
                                <p style="font-size: 14px; color: #475569; margin: 0 0 10px 0;">{item.get('what_it_does', '')}</p>
                                <div style="background-color: #F0F9FF; border-left: 3px solid #0284C7; padding: 10px 14px; font-size: 13px; color: #0369A1;">
                                    <strong>Daily Use Case:</strong> {item.get('daily_use_case', '')}
                                </div>
                            </div>
                """

    # FOOTER
    html_content += f"""
                        </td>
                    </tr>
                    
                    <tr>
                        <td style="padding: 24px 32px; background-color: #F8FAFC; border-top: 1px solid #E2E8F0; text-align: center;">
                            <p style="margin: 0; font-size: 11px; color: #94A3B8; font-weight: 500;">
                                BUILDR.ai &bull; Daily AI Automation Intelligence &bull; Delivered automatically
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
    """

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Successfully generated HTML newsletter to {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_html()
