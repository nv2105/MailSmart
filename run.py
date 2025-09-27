import uvicorn

if __name__ == "__main__":
    port = 8000
    print(f"\n🚀 MailSmart API live on http://127.0.0.1:{port} (Swagger docs: /docs)\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)
