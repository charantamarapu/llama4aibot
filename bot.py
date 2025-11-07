import os
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleSanskritBot:
    """Direct model access without RAG, memory, or database"""
    
    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "meta-llama/llama-4-maverick:free"
        self.user_conversations = {}
    
    def call_model(self, user_id, question):
        """Direct model call with basic conversation history"""
        try:
            if user_id not in self.user_conversations:
                self.user_conversations[user_id] = []
            
            self.user_conversations[user_id].append({
                "role": "user",
                "content": question
            })
            
            if len(self.user_conversations[user_id]) > 10:
                self.user_conversations[user_id] = self.user_conversations[user_id][-10:]
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a Sanskrit expert. Answer questions directly and concisely."
                }
            ]
            messages.extend(self.user_conversations[user_id])
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/yourusername/sanskritbot",
                "X-Title": "Sanskrit Bot"
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

bot = SimpleSanskritBot()

# Health check handler for Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Bot is running')
    
    def log_message(self, format, *args):
        pass  # Suppress logs

def run_health_server():
    """Run simple HTTP server for Render health checks"""
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"🏥 Health check server running on port {port}")
    server.serve_forever()

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
    
    if text == "🗑️ Clear Chat":
        bot.clear_conversation(user_id)
        await update.message.reply_text("✓ Chat cleared!")
        await update.message.delete()
        return
    
    thinking = await update.message.reply_text("⌛ Processing...")
    answer = bot.call_model(user_id, text)
    await thinking.delete()
    await update.message.reply_text(answer)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(msg="Error:", exc_info=context.error)

def main():
    """Start bot"""
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("ERROR: Set TELEGRAM_BOT_TOKEN environment variable")
        return
    
    # Start health check server in background thread
    health_thread = Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_error_handler(error_handler)
    
    print("🤖 Simple Sanskrit Bot")
    print("="*40)
    print("🔌 Direct OpenRouter Connection")
    print("📝 Basic Conversation Memory")
    print("="*40)
    print("Press Ctrl+C to stop")
    
    app.run_polling()

if __name__ == '__main__':
    main()
