import os
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleSanskritBot:
    def __init__(self):
        # Read from environment variable (for Render deployment)
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
            
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "meta-llama/llama-4-maverick:free"
        self.user_conversations = {}
    
    def call_model(self, user_id, question):
        """Direct model call with basic conversation history"""
        try:
            # Initialize conversation if needed
            if user_id not in self.user_conversations:
                self.user_conversations[user_id] = []
            
            # Add current question to conversation
            self.user_conversations[user_id].append({
                "role": "user",
                "content": question
            })
            
            # Keep only last 10 messages to avoid token limits
            if len(self.user_conversations[user_id]) > 10:
                self.user_conversations[user_id] = self.user_conversations[user_id][-10:]
            
            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": "You are a Sanskrit expert. Answer questions directly and concisely."
                }
            ]
            messages.extend(self.user_conversations[user_id])
            
            # API call
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 1000
            }
            
            response = requests.post(
                self.openrouter_url, 
                json=data, 
                headers=headers, 
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                answer = result['choices'][0]['message']['content']
                # Add assistant response to conversation
                self.user_conversations[user_id].append({
                    "role": "assistant",
                    "content": answer
                })
                return answer
            else:
                return f"Error: Unexpected API response"
                
        except requests.exceptions.Timeout:
            return "Error: Request timeout. Please try again."
        except requests.exceptions.RequestException as e:
            return f"Error: API request failed: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def clear_conversation(self, user_id):
        """Clear conversation history"""
        if user_id in self.user_conversations:
            self.user_conversations[user_id] = []

# Initialize bot
bot = SimpleSanskritBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    keyboard = [["🗑️ Clear Chat"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    message = """🙏 Namaste!

Welcome to Sanskrit Bot!

Direct connection to Llama model.
Type any question to chat!"""
    
    await update.message.reply_text(message, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Check for Clear button
    if text == "🗑️ Clear Chat":
        bot.clear_conversation(user_id)
        await update.message.reply_text("✓ Chat cleared!")
        await update.message.delete()
        return
    
    # Process question
    thinking = await update.message.reply_text("⌛ Processing...")
    answer = bot.call_model(user_id, text)
    await thinking.delete()
    await update.message.reply_text(answer)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(msg="Error:", exc_info=context.error)

def main():
    """Start bot"""
    TOKEN = "8277012435:AAHLywMKJLcC7DizR-8MSeKY4VX-CbTHOCg"
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_error_handler(error_handler)
    
    print("\n🤖 Simple Sanskrit Bot")
    print("="*40)
    print("🔌 Direct OpenRouter Connection")
    print("📝 Basic Conversation Memory (in-memory only)")
    print("="*40)
    print("Press Ctrl+C to stop\n")
    
    app.run_polling()

if __name__ == '__main__':
    main()
