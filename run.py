from app import create_app
from app.services.file_service import FileService
from app.services.search_service import SearchService

app = create_app()

# Initialize search index at startup
with app.app_context():
    file_service = FileService(app)
    search_service = SearchService(file_service)
    search_service.build_search_index()

if __name__ == '__main__':
    print("\nStarting ivrit.ai Explore...")
    print("Search index is ready. Queries should be much faster now.")
    app.run(debug=True, port=5000, host='0.0.0.0') 