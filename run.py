from app import create_app
from dotenv import load_dotenv
import os

# Load environment variables first
load_dotenv()

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Print debug info
    print("Environment variables loaded:")
    print(f"GROQ_API_KEY: {'*' * 8 + os.getenv('GROQ_API_KEY', '')[-4:] if os.getenv('GROQ_API_KEY') else 'Not set'}")
    
    # Run the app
    app.run(debug=True)
