from app import create_app

app = create_app()

if __name__ == '__main__':
    print("\nStarting ivrit.ai Explore...")
    app.run(debug=True, port=5000, host='0.0.0.0') 