import sqlite3
import os
import webbrowser
import requests
keyword = input("What would you like to search for? ")
with open('result.html', 'w') as html:
    html.write("<!DOCTYPE html>\n")
    html.write("<html>\n<body>\n")
    con = sqlite3.connect('proj.db')
    cur = con.cursor()
    results = cur.execute(f"SELECT hrefs, alts FROM hashes WHERE alts LIKE '%{keyword}%'").fetchall()
    for result in results:
        for url in result[0].split('\n'):
            if requests.head(url).status_code == 200:
                html.write(f'<img src="{url}">\n')
    html.write("</body>\n</html>")
#webbrowser.open('file://' + os.path.abspath("result.html"), new = 2)
