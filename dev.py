"""Development server script."""
import uvicorn


def main():
    """Run the development server."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

