print("🔥 USING NEW PDF GENERATOR")
from playwright.async_api import async_playwright

from datetime import datetime

async def generate_pdf(record, audit):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""
    <html>
    <h1 style="color:red;">NEW PDF VERSION</h1>
    <head>
        <style>
            @page {{
                size: A4;
                margin: 20mm;
            }}

            body {{
                font-family: "Times New Roman", serif;
                position: relative;
            }}

            .page {{
                position: relative;
                width: 100%;
                height: 100%;
            }}

            /* WATERMARK */
            .watermark {{
                position: absolute;
                top: 40%;
                left: 50%;
                transform: translate(-50%, -50%) rotate(-30deg);
                font-size: 40px;
                color: rgba(0,0,0,0.08);
                text-align: center;
                white-space: nowrap;
            }}

            .header {{
                font-size: 24px;
                font-weight: bold;
                border-bottom: 1px solid black;
                padding-bottom: 5px;
                margin-bottom: 10px;
            }}

            .layout {{
                display: flex;
                gap: 20px;
            }}

            .left {{
                flex: 3;
            }}

            .right {{
                flex: 1;
                border-left: 1px solid #000;
                padding-left: 10px;
                font-size: 12px;
            }}

            .field {{
                margin-bottom: 6px;
            }}

            .label {{
                font-weight: bold;
            }}

            .footer {{
                position: absolute;
                bottom: 0;
                width: 100%;
                border-top: 1px solid black;
                font-size: 10px;
                padding-top: 5px;
            }}

            .signature {{
                margin-top: 40px;
            }}

            .line {{
                border-bottom: 1px solid black;
                width: 200px;
                margin-bottom: 5px;
            }}

        </style>
    </head>

    <body>
        <div class="page">

            <div class="watermark">
                ATHENAEUM ORBIS<br/>INTERNAL
            </div>

            <div class="header">
                {record.get("title", "")}
            </div>

            <div class="layout">

                <!-- LEFT -->
                <div class="left">

                    <div class="field"><span class="label">Author:</span> {record.get("author","")}</div>
                    <div class="field"><span class="label">Publisher:</span> {record.get("publisher","")}</div>
                    <div class="field"><span class="label">Year:</span> {record.get("year","")}</div>

                    <hr>

                    <div class="field"><span class="label">DDC:</span> {record.get("ddc","")}</div>
                    <div class="field"><span class="label">Category:</span> {record.get("category","")}</div>
                    <div class="field"><span class="label">Language:</span> {record.get("language","")}</div>

                    <div class="signature">
                        <div class="line"></div>
                        Authorized Archivist
                    </div>

                </div>

                <!-- RIGHT SIDEBAR -->
                <div class="right">

                    <div class="field"><span class="label">Record ID:</span><br>{record.get("serial_no","")}</div>
                    <div class="field"><span class="label">User:</span><br>{audit.get("userName","")}</div>
                    <div class="field"><span class="label">Device:</span><br>{audit.get("deviceID","")}</div>
                    <div class="field"><span class="label">Printed:</span><br>{timestamp}</div>

                </div>

            </div>

            <!-- FOOTER -->
            <div class="footer">
                ATHENAEUM ORBIS • ARCHIVAL SYSTEM • {timestamp}
            </div>

        </div>
    </body>
    </html>
    """

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.set_content(html)

        pdf = await page.pdf(
            format="A4",
            print_background=True
        )

        await browser.close()

        return pdf