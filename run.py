# run.py
import uvicorn

if __name__ == "__main__":
    port = int(__import__("os").environ.get("PORT", 8000))
    print(f"\n🚀 MailSmart API live on http://127.0.0.1:{port} (Swagger docs: /docs)\n")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
