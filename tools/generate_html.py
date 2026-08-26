#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime

# Define file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".tmp")
SYNTHESIZED_NEWS_FILE = os.path.join(TMP_DIR, "synthesized_news.json")
OUTPUT_HTML_FILE = os.path.join(TMP_DIR, "newsletter.html")

def render_html():
    if not os.path.exists(SYNTHESIZED_NEWS_FILE):
        print(f"Error: {SYNTHESIZED_NEWS_FILE} not found. Run ai_research.py first.")
        sys.exit(1)
        
    with open(SYNTHESIZED_NEWS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    current_date = datetime.now().strftime("%B %d, %Y")
    current_day = datetime.now().strftime("%A").upper()
    
    launches = data.get("launches", [])
    prompting = data.get("prompting_and_technique", [])
    head_to_head = data.get("head_to_head", [])
    tech_shifts = data.get("tech_shifts", [])
    repo_radar = data.get("repo_radar", [])
    business_ai = data.get("business_ai", [])
    senior_engineer = data.get("senior_engineer", [])
    
    total_items = (
        len(launches) + len(prompting) + len(head_to_head) +
        len(tech_shifts) + len(repo_radar) + len(business_ai) + len(senior_engineer)
    )
    
    # Estimate reading time (approx 25 seconds per item)
    read_mins = max(3, round((total_items * 35) / 60))
    
    # repobuilt modern aesthetic newsletter template
    html_content = f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>repobuilt // Daily Engineering Intelligence</title>
    <!--[if gte mso 9]>
    <xml>
      <o:OfficeDocumentSettings>
        <o:AllowPNG/>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
    <![endif]-->
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
        
        /* Reset and client-specific overrides */
        body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse !important; }}
        img {{ -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }}
        
        body {{ 
            height: 100% !important; 
            margin: 0 !important; 
            padding: 0 !important; 
            width: 100% !important; 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            background-color: #0F172A; 
            color: #1E293B; 
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        
        a {{ color: #4F46E5; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}

        /* Responsive Breakpoints */
        @media only screen and (max-width: 660px) {{
            .main-wrapper {{ padding: 0 !important; }}
            .content-table {{ width: 100% !important; max-width: 100% !important; border-radius: 0 !important; border-left: none !important; border-right: none !important; }}
            .header-cell {{ padding: 28px 20px 20px 20px !important; }}
            .body-cell {{ padding: 24px 18px !important; }}
            .footer-cell {{ padding: 28px 18px !important; }}
            .mobile-stack {{ display: block !important; width: 100% !important; }}
            .mobile-meta {{ text-align: left !important; margin-top: 6px !important; }}
            .item-title {{ font-size: 17px !important; line-height: 1.4 !important; }}
            .code-snippet {{ font-size: 11px !important; padding: 10px 12px !important; }}
            .brand-pill {{ display: none !important; }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #0B0F19; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B;">
    <table class="main-wrapper" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%; background-color: #0B0F19; padding: 32px 0 48px 0; table-layout: fixed;">
        <tr>
            <td align="center" style="padding: 0 12px;">
                <!-- MAIN CONTAINER -->
                <table class="content-table" width="620" cellpadding="0" cellspacing="0" border="0" style="max-width: 620px; width: 620px; background-color: #FFFFFF; border-radius: 12px; border: 1px solid #1E293B; overflow: hidden; box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);">
                    
                    <!-- BRAND HEADER -->
                    <tr>
                        <td class="header-cell" style="padding: 32px 32px 24px 32px; background-color: #0F172A; border-bottom: 1px solid #1E293B;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td valign="middle">
                                        <div style="font-size: 24px; font-weight: 800; letter-spacing: -0.04em; line-height: 1;">
                                            <a href="https://repobuilt.com" target="_blank" style="color: #FFFFFF; text-decoration: none;">
                                                <span style="color: #F8FAFC;">repo</span><span style="color: #6366F1;">built</span>
                                            </a>
                                        </div>
                                        <div style="margin-top: 6px; font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.12em; text-transform: uppercase;">
                                            ENGINEERING INTELLIGENCE &bull; {current_day}, {current_date}
                                        </div>
                                    </td>
                                    <td class="brand-pill" align="right" valign="middle">
                                        <span style="display: inline-block; background-color: #1E293B; color: #38BDF8; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 20px; border: 1px solid #334155; letter-spacing: 0.05em;">
                                            {read_mins} MIN READ &bull; 7 SECTIONS
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- SUBHEADER TICKER -->
                    <tr>
                        <td style="padding: 10px 32px; background-color: #1E293B; border-bottom: 1px solid #334155;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="font-size: 11px; color: #CBD5E1; font-weight: 500;">
                                        <span style="color: #10B981; font-weight: 700;">● LIVE DISPATCH</span> &nbsp;|&nbsp; Daily curated signal for software engineers, architects & builders.
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- MAIN BODY -->
                    <tr>
                        <td class="body-cell" style="padding: 32px 32px 16px 32px; background-color: #FFFFFF;">
    """
    
    if total_items == 0:
        html_content += """
                            <div style="text-align: center; padding: 48px 16px;">
                                <p style="font-size: 15px; color: #64748B; font-weight: 500;">No briefing compiles available for this cycle.</p>
                            </div>
        """
    else:
        # =========================================================================
        # SECTION 1: LAUNCHES & RELEASES (Indigo)
        # =========================================================================
        if launches:
            html_content += """
                            <!-- SECTION HEADER: LAUNCHES -->
                            <div style="margin-top: 8px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #6366F1;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td>
                                            <span style="font-size: 12px; font-weight: 800; color: #6366F1; letter-spacing: 0.12em; text-transform: uppercase;">01 // LAUNCHES & RELEASES</span>
                                        </td>
                                        <td align="right" style="font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.05em;">
                                            MODELS &bull; TOOLS &bull; ANNOUNCEMENTS
                                        </td>
                                    </tr>
                                </table>
                            </div>
            """
            for item in launches:
                html_content += f"""
                            <div style="padding-bottom: 28px; margin-bottom: 28px; border-bottom: 1px solid #F1F5F9;">
                                <h2 class="item-title" style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0; line-height: 1.4; letter-spacing: -0.02em;">
                                    <a href="{item['url']}" target="_blank" style="color: #0F172A; text-decoration: none;">{item['title']}</a>
                                </h2>
                                <div style="font-size: 11px; color: #64748B; margin-bottom: 14px; font-weight: 500;">
                                    <span style="display: inline-block; background-color: #EEF2FF; color: #4F46E5; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; margin-right: 6px;">Source</span> {item['source']}
                                </div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">What It Is</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 12px 0;">{item['what_it_is']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">Technical Specs</div>
                                <div class="code-snippet" style="background-color: #F8FAFC; border-left: 3px solid #6366F1; border-radius: 0 6px 6px 0; padding: 12px 14px; font-size: 12px; line-height: 1.6; color: #1E293B; margin-bottom: 12px; font-family: 'JetBrains Mono', SFMono-Regular, Consolas, monospace;">
                                    {item['details']}
                                </div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">Why It Matters</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 14px 0;">{item['why_it_matters']}</p>
                                
                                <a href="{item['url']}" target="_blank" style="display: inline-block; color: #4F46E5; font-weight: 600; font-size: 13px; text-decoration: none;">View announcement &rarr;</a>
                            </div>
                """

        # =========================================================================
        # SECTION 2: PROMPTING & TECHNIQUE (Sky/Cyan)
        # =========================================================================
        if prompting:
            html_content += """
                            <!-- SECTION HEADER: PROMPTING -->
                            <div style="margin-top: 8px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #0284C7;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td>
                                            <span style="font-size: 12px; font-weight: 800; color: #0284C7; letter-spacing: 0.12em; text-transform: uppercase;">02 // PROMPTING & PATTERNS</span>
                                        </td>
                                        <td align="right" style="font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.05em;">
                                            SYSTEM PROMPTS &bull; WORKFLOWS
                                        </td>
                                    </tr>
                                </table>
                            </div>
            """
            for item in prompting:
                html_content += f"""
                            <div style="padding-bottom: 28px; margin-bottom: 28px; border-bottom: 1px solid #F1F5F9;">
                                <h2 class="item-title" style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0; line-height: 1.4; letter-spacing: -0.02em;">
                                    <a href="{item['url']}" target="_blank" style="color: #0F172A; text-decoration: none;">{item['title']}</a>
                                </h2>
                                <div style="font-size: 11px; color: #64748B; margin-bottom: 14px; font-weight: 500;">
                                    <span style="display: inline-block; background-color: #E0F2FE; color: #0369A1; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; margin-right: 6px;">Pattern</span> {item['technique']} &bull; Source: {item['source']}
                                </div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">How to Apply</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 12px 0;">{item['how_to_apply']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">Pattern / Example Template</div>
                                <div class="code-snippet" style="background-color: #0B0F19; border: 1px solid #1E293B; border-left: 3px solid #0284C7; padding: 12px 14px; border-radius: 6px; font-size: 12px; line-height: 1.6; color: #F1F5F9; margin-bottom: 14px; font-family: 'JetBrains Mono', SFMono-Regular, Consolas, monospace; white-space: pre-wrap; word-break: break-word;">{item['example']}</div>
                                
                                <a href="{item['url']}" target="_blank" style="display: inline-block; color: #0284C7; font-weight: 600; font-size: 13px; text-decoration: none;">Explore implementation &rarr;</a>
                            </div>
                """

        # =========================================================================
        # SECTION 3: HEAD TO HEAD (Orange/Amber)
        # =========================================================================
        if head_to_head:
            html_content += """
                            <!-- SECTION HEADER: HEAD TO HEAD -->
                            <div style="margin-top: 8px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #EA580C;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td>
                                            <span style="font-size: 12px; font-weight: 800; color: #EA580C; letter-spacing: 0.12em; text-transform: uppercase;">03 // HEAD TO HEAD</span>
                                        </td>
                                        <td align="right" style="font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.05em;">
                                            BENCHMARKS &bull; ARCHITECTURE TRADEOFFS
                                        </td>
                                    </tr>
                                </table>
                            </div>
            """
            for item in head_to_head:
                contenders_str = " vs ".join(item.get("contenders", []))
                html_content += f"""
                            <div style="padding-bottom: 28px; margin-bottom: 28px; border-bottom: 1px solid #F1F5F9;">
                                <h2 class="item-title" style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0; line-height: 1.4; letter-spacing: -0.02em;">
                                    <a href="{item['url']}" target="_blank" style="color: #0F172A; text-decoration: none;">{item['title']}</a>
                                </h2>
                                <div style="font-size: 11px; color: #EA580C; margin-bottom: 14px; font-weight: 700; font-family: 'JetBrains Mono', monospace;">
                                    [ {contenders_str} ]
                                </div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">Verdict & Analysis</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 12px 0;">{item['verdict']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #9A3412; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">Decision Matrix // When to Choose Which</div>
                                <div style="background-color: #FFF7ED; border-left: 3px solid #EA580C; border-radius: 0 6px 6px 0; padding: 12px 14px; font-size: 13px; line-height: 1.6; color: #9A3412; margin-bottom: 14px; font-weight: 500;">
                                    {item['use_when']}
                                </div>
                                
                                <a href="{item['url']}" target="_blank" style="display: inline-block; color: #EA580C; font-weight: 600; font-size: 13px; text-decoration: none;">View benchmark data &rarr;</a>
                            </div>
                """

        # =========================================================================
        # SECTION 4: TECH SHIFTS & INFRASTRUCTURE (Emerald)
        # =========================================================================
        if tech_shifts:
            html_content += """
                            <!-- SECTION HEADER: TECH SHIFTS -->
                            <div style="margin-top: 8px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #059669;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td>
                                            <span style="font-size: 12px; font-weight: 800; color: #059669; letter-spacing: 0.12em; text-transform: uppercase;">04 // TECH SHIFTS & INFRA</span>
                                        </td>
                                        <td align="right" style="font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.05em;">
                                            DEPRECATIONS &bull; INCIDENTS &bull; PLATFORMS
                                        </td>
                                    </tr>
                                </table>
                            </div>
            """
            for item in tech_shifts:
                html_content += f"""
                            <div style="padding-bottom: 28px; margin-bottom: 28px; border-bottom: 1px solid #F1F5F9;">
                                <h2 class="item-title" style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0; line-height: 1.4; letter-spacing: -0.02em;">
                                    <a href="{item['url']}" target="_blank" style="color: #0F172A; text-decoration: none;">{item['title']}</a>
                                </h2>
                                <div style="font-size: 11px; color: #64748B; margin-bottom: 14px; font-weight: 500;">
                                    <span style="display: inline-block; background-color: #ECFDF5; color: #047857; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; margin-right: 6px;">Source</span> {item['source']}
                                </div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">Shift Summary</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 12px 0;">{item['what_it_is']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">Technical Details</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 12px 0;">{item['details']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #065F46; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">Impact on Production Systems</div>
                                <div style="background-color: #ECFDF5; border-left: 3px solid #059669; border-radius: 0 6px 6px 0; padding: 12px 14px; font-size: 13px; line-height: 1.6; color: #065F46; margin-bottom: 14px;">
                                    {item['why_it_matters']}
                                </div>
                                
                                <a href="{item['url']}" target="_blank" style="display: inline-block; color: #059669; font-weight: 600; font-size: 13px; text-decoration: none;">Read shift breakdown &rarr;</a>
                            </div>
                """

        # =========================================================================
        # SECTION 5: REPO RADAR (Violet)
        # =========================================================================
        if repo_radar:
            html_content += """
                            <!-- SECTION HEADER: REPO RADAR -->
                            <div style="margin-top: 8px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #7C3AED;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td>
                                            <span style="font-size: 12px; font-weight: 800; color: #7C3AED; letter-spacing: 0.12em; text-transform: uppercase;">05 // REPO RADAR</span>
                                        </td>
                                        <td align="right" style="font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.05em;">
                                            OPEN-SOURCE &bull; ARCHITECTURES
                                        </td>
                                    </tr>
                                </table>
                            </div>
            """
            for repo in repo_radar:
                stars_formatted = f"★ {repo['stars']:,}"
                html_content += f"""
                            <div style="padding: 18px 20px; margin-bottom: 20px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 10px;">
                                    <tr>
                                        <td class="mobile-stack">
                                            <a href="{repo['html_url']}" target="_blank" style="font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 700; color: #4F46E5; text-decoration: none;">
                                                {repo['full_name']}
                                            </a>
                                        </td>
                                        <td class="mobile-stack mobile-meta" align="right">
                                            <span style="display: inline-block; font-size: 11px; font-weight: 700; background-color: #EEF2FF; color: #4F46E5; padding: 2px 8px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; margin-right: 4px;">{stars_formatted}</span>
                                            <span style="display: inline-block; font-size: 11px; font-weight: 600; background-color: #E2E8F0; color: #334155; padding: 2px 8px; border-radius: 4px; font-family: 'JetBrains Mono', monospace;">{repo['language']}</span>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 12px 0;">{repo['what_it_does']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 10px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">Daily Developer Use Case</div>
                                <div style="font-size: 13px; line-height: 1.5; color: #334155; margin: 0 0 12px 0; background-color: #FFFFFF; padding: 10px 12px; border-radius: 6px; border: 1px solid #E2E8F0;">
                                    {repo['daily_use_case']}
                                </div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 10px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">Quick Start / Install Command</div>
                                <div class="code-snippet" style="background-color: #0B0F19; border: 1px solid #1E293B; color: #38BDF8; font-family: 'JetBrains Mono', SFMono-Regular, Consolas, monospace; font-size: 12px; padding: 10px 12px; border-radius: 6px; margin-bottom: 12px; word-break: break-all;">
                                    $ {repo['getting_started']}
                                </div>
                                
                                <a href="{repo['html_url']}" target="_blank" style="display: inline-block; color: #4F46E5; font-weight: 600; font-size: 13px; text-decoration: none;">View repository on GitHub &rarr;</a>
                            </div>
                """

        # =========================================================================
        # SECTION 6: AI IN BUSINESS (Gold/Amber)
        # =========================================================================
        if business_ai:
            html_content += """
                            <!-- SECTION HEADER: BUSINESS AI -->
                            <div style="margin-top: 8px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #D97706;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td>
                                            <span style="font-size: 12px; font-weight: 800; color: #D97706; letter-spacing: 0.12em; text-transform: uppercase;">06 // AI IN BUSINESS</span>
                                        </td>
                                        <td align="right" style="font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.05em;">
                                            ENTERPRISE DEPLOYMENTS &bull; ROI
                                        </td>
                                    </tr>
                                </table>
                            </div>
            """
            for item in business_ai:
                html_content += f"""
                            <div style="padding-bottom: 28px; margin-bottom: 28px; border-bottom: 1px solid #F1F5F9;">
                                <h2 class="item-title" style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0; line-height: 1.4; letter-spacing: -0.02em;">
                                    <a href="{item['url']}" target="_blank" style="color: #0F172A; text-decoration: none;">{item['title']}</a>
                                </h2>
                                <div style="font-size: 11px; color: #64748B; margin-bottom: 14px; font-weight: 500;">
                                    <span style="display: inline-block; background-color: #FEF3C7; color: #92400E; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; margin-right: 6px;">{item['company']}</span>
                                    Source: {item['source']}
                                </div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">What They Deployed</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 12px 0;">{item['what_they_did']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #92400E; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">Business Impact & Measurable ROI</div>
                                <div style="background-color: #FFFBEB; border-left: 3px solid #D97706; border-radius: 0 6px 6px 0; padding: 12px 14px; font-size: 13px; line-height: 1.6; color: #92400E; margin-bottom: 12px; font-weight: 500;">
                                    {item['business_impact']}
                                </div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">Builder Takeaway</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 14px 0;">{item['takeaway_for_builders']}</p>
                                
                                <a href="{item['url']}" target="_blank" style="display: inline-block; color: #D97706; font-weight: 600; font-size: 13px; text-decoration: none;">Read full analysis &rarr;</a>
                            </div>
                """

        # =========================================================================
        # SECTION 7: SENIOR ENGINEER (Rose/Crimson)
        # =========================================================================
        if senior_engineer:
            html_content += """
                            <!-- SECTION HEADER: SENIOR ENGINEER -->
                            <div style="margin-top: 8px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #E11D48;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td>
                                            <span style="font-size: 12px; font-weight: 800; color: #E11D48; letter-spacing: 0.12em; text-transform: uppercase;">07 // SENIOR ENGINEER</span>
                                        </td>
                                        <td align="right" style="font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.05em;">
                                            PRODUCTION WISDOM &bull; WAR STORIES
                                        </td>
                                    </tr>
                                </table>
                            </div>
            """
            for item in senior_engineer:
                html_content += f"""
                            <div style="padding-bottom: 28px; margin-bottom: 28px; border-bottom: 1px solid #F1F5F9;">
                                <h2 class="item-title" style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0; line-height: 1.4; letter-spacing: -0.02em;">
                                    <a href="{item['url']}" target="_blank" style="color: #0F172A; text-decoration: none;">{item['title']}</a>
                                </h2>
                                <div style="font-size: 11px; color: #64748B; margin-bottom: 14px; font-weight: 500;">
                                    <span style="display: inline-block; background-color: #FFE4E6; color: #BE123C; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; margin-right: 6px;">{item['topic_area']}</span>
                                    Source: {item['source']}
                                </div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #475569; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">The Production Lesson</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #1E293B; margin: 0 0 12px 0; font-weight: 600;">{item['the_lesson']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #BE123C; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">&#9888; Why It Bites You in Production</div>
                                <div style="background-color: #FFF1F2; border-left: 3px solid #E11D48; border-radius: 0 6px 6px 0; padding: 12px 14px; font-size: 13px; line-height: 1.6; color: #9F1239; margin-bottom: 12px; font-weight: 500;">
                                    {item['why_it_bites']}
                                </div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #047857; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.06em;">&#10003; Battle-Tested Solution</div>
                                <div class="code-snippet" style="background-color: #ECFDF5; border: 1px solid #A7F3D0; border-left: 3px solid #059669; border-radius: 0 6px 6px 0; padding: 12px 14px; font-size: 12px; line-height: 1.6; color: #065F46; margin-bottom: 14px; font-family: 'JetBrains Mono', SFMono-Regular, Consolas, monospace; word-break: break-word;">
                                    {item['the_fix']}
                                </div>
                                
                                <a href="{item['url']}" target="_blank" style="display: inline-block; color: #E11D48; font-weight: 600; font-size: 13px; text-decoration: none;">Read full breakdown &rarr;</a>
                            </div>
                """

    html_content += """
                        </td>
                    </tr>
                    
                    <!-- FOOTER -->
                    <tr>
                        <td class="footer-cell" style="padding: 32px; text-align: left; font-size: 11px; color: #64748B; background-color: #0F172A; border-top: 1px solid #1E293B;">
                            <div style="font-size: 16px; font-weight: 800; color: #F8FAFC; margin-bottom: 8px;">
                                <span style="color: #F8FAFC;">repo</span><span style="color: #6366F1;">built</span>
                            </div>
                            <p style="margin: 0 0 10px 0; line-height: 1.6; color: #94A3B8;">
                                Engineering intelligence, architecture shifts, and production-tested patterns delivered daily.
                            </p>
                            <p style="margin: 0 0 14px 0; line-height: 1.6; color: #64748B;">
                                Automated synthesis powered by verified RSS feeds, GitHub release monitors, and developer intelligence pipelines.
                            </p>
                            <div style="padding-top: 12px; border-top: 1px solid #1E293B; font-size: 10px; color: #475569;">
                                &copy; 2026 repobuilt. All rights reserved. &bull; 
                                <a href="#" style="color: #64748B; text-decoration: underline;">Preferences</a> &bull; 
                                <a href="#" style="color: #64748B; text-decoration: underline;">Unsubscribe</a>
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
    """
    
    with open(OUTPUT_HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Successfully generated HTML newsletter to {OUTPUT_HTML_FILE}")

if __name__ == "__main__":
    render_html()
