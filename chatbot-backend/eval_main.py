from conversation.conversation_processor import process_and_store_conversations
import asyncio
############################################################################################################

if __name__ == "__main__":
    user_id = "eval-user"
    thread_id = "eval-session"
   
    asyncio.run(process_and_store_conversations(version_id= 6, user_id=user_id, thread_id=thread_id))