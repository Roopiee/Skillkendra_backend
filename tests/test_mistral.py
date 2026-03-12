"""Test Mistral API connection"""

import os
from dotenv import load_dotenv
from mistralai import Mistral

# Load environment variables
load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")

if not api_key:
    print("❌ MISTRAL_API_KEY not found in .env file!")
    print("\n📝 Create a .env file with:")
    print("   MISTRAL_API_KEY=your_key_here")
    exit(1)

print("✅ API key loaded")
print(f"   Key starts with: {api_key[:10]}...")

# Test connection
print("\n🧪 Testing Mistral API...")

try:
    client = Mistral(api_key=api_key)
    
    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[
            {"role": "user", "content": "Say 'Hello from Mistral!' and nothing else."}
        ]
    )
    
    result = response.choices[0].message.content
    print(f"✅ Mistral responded: {result}")
    print("\n🎉 Connection successful!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n💡 Check:")
    print("   1. API key is correct")
    print("   2. You have credits on Mistral")
    print("   3. Internet connection works")

