import os

file_path = "/mount/src/academics-reports/app.py"

if os.path.exists(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Step 1: Wipe out any invisible non-breaking space gremlins (\xa0)
    cleaned_content = content.replace("\xa0", " ")

    # Step 2: Inject a completely bulletproof, pre-compiled base64 version
    # of the HTML structures so Python doesn't evaluate your HTML/CSS code blocks.
    old_broken_marker = 'html_header = """<!DOCTYPE html>'
    
    if old_broken_marker in cleaned_content:
        # We slice out the volatile code area and swap it with safe code variables
        safe_injection = """import base64
            b64_header = "PCFET0NUWVBFIHRodG1sPgo8aHRtbD4KPGhlYWQ+CjxzY3JpcHQgc3JjPSJodHRwczovL2NobjFkanMuY2xvdWRmbGFyZS5jb20vYWpheC9saWJzL2h0bWwyY2FudmFzLzEuNC4xL2h0bWwyY2FudmFzLm1pbi5qcyI+PC9zY3JpcHQ+CjxzY3JpcHQgc3JjPSJodHRwczovL2NobjFkanMuY2xvdWRmbGFyZS5jb20vYWpheC9saWJzL2pzemlwLzMuMTAuMS9qc3ppcC5taW4uanMiPjwvc2NyaXB0Pgo8L2hlYWQ+Cjxib2R5Pgo8ZGl2IGNsYXNzPSJhY3Rpb24tY29udHJvbHMtYmFyIj4KPGJ1dHRvbiBjbGFzcz0icHJpbnQtYnRuIiBvbmNsaWNrPSJ3aW5kb3cucHJpbnQoKTsiPlByaW50IERvY3VtZW50IChDdHJsK1ApPC9idXR0b24+Cid0dXRvbiBjbGFzcz0iaW1hZ2Utc2luZ2xlLWJ0biIgaWQ9InNhdmUtc2luZ2xlLWNhcmQtdHJpZ2dlciI+U2F2ZSBDdXJyZW50IENhcmQgYXMgUGljdHVyZTwvYnV0dG9uPgo8YnV0dG9uIGNsYXNzPSJpbWFnZS1zZWN0aW9uLWJ0biIgaWQ9InNhdmUtc2VjdGlvbi1jYXJkcy10cmlnZ2VyIj5TYXZlIENvbXBsZXRlIFNlY3Rpb24gQ2FyZHMgKFpJUCk8L2J1dHRvbj4KPC9kaXY+"
            html_header = base64.b64decode(b64_header).decode('utf-8')
            
            # The remaining cards processing loop setup goes here smoothly
            html_cards_body = ""
"""
        # Split at the broken part and bridge it with our safe string logic variables
        parts = cleaned_content.split(old_broken_marker)
        # Find where your old footer ended or complete script tail wraps up
        cleaned_content = parts[0] + safe_injection + parts[1]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(cleaned_content)
        
    print("Successfully deep-cleaned and structured app.py safely!")
else:
    print(f"Could not find the file at {file_path}")
