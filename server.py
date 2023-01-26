import asyncio
import aiosqlite
import json
from sanic import Sanic, response

app = Sanic(__name__)


@app.listener('before_server_start')
async def setup_db(app_, loop):
    app_.ctx.db = await aiosqlite.connect('redirects.db', loop=loop)
    await app_.ctx.db.execute('''CREATE TABLE IF NOT EXISTS redirects (
                                short_code TEXT,
                                redirect_url TEXT
                            )''')
    await app_.ctx.db.execute('''CREATE TABLE IF NOT EXISTS statistics (
                                destination TEXT,
                                visits BLOB,
                                meta_data BLOB
                            )''')
    await app_.ctx.db.commit()


@app.route("/<short_code>")
async def redirect(request, short_code):
    async with app.ctx.db.execute("SELECT redirect_url FROM redirects WHERE short_code = ?", (short_code,)) as cursor:
        redirect_url = await cursor.fetchone()
    if redirect_url:
        redirect_url = redirect_url[0]
        # update statistics
        await app.ctx.db.execute("INSERT INTO statistics (destination, meta_data) VALUES (?, ?)",
                                 (redirect_url, json.dumps(dict(request.headers))))
        await app.ctx.db.commit()
        # redirect to redirect_url
        return response.redirect(redirect_url)
    else:
        return response.text("Short code not found", status=404)


@app.route("/register", methods=["POST"])
async def register_shortcode(request):
    short_code = request.json.get("short_code")
    redirect_url = request.json.get("redirect_url")
    if short_code and redirect_url:
        async with app.ctx.db.execute("INSERT INTO redirects (short_code, redirect_url) VALUES (?, ?)",
                                      (short_code, redirect_url)) as cursor:
            await app.ctx.db.commit()
        return response.json({"status": "success"})
    else:
        return response.json({"status": "error", "message": "Both short_code and redirect_url are required"})


@app.route("/redirects")
async def get_redirects(request):
    async with app.ctx.db.execute("SELECT short_code, redirect_url FROM redirects") as cursor:
        redirects = await cursor.fetchall()
    return response.json(redirects)

@app.route("/register", methods=["GET"])
async def register_shortcode_html(request):
    return await response.file('template.html')
# run server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
