from langchain_core.messages import HumanMessage 

class Summarizer:
    
    def __init__(self, model):
        self.model = model
     
         
    async def summerize_AI_message(self, message:str):
            
            summary_prompt = (
                "Summarize the following AI message into a concise response."
                "Include only the most important details and specific information. Avoid repeating or expanding the content. "
                "Do not add unnecessary context or embellishments.\n\n"
                "Here is the content to summarize:\n\n"
            )
            
            input_message = [
            HumanMessage(content=summary_prompt + message)
            ]

            # Generate the summary
            summary_message = await self.model.ainvoke(input_message)

            
            return summary_message.content
        
    
    async def __call__(self, message: str) -> str:
        """
        Allows the Summarizer instance to be called as a function to summarize a message.

        Args:
            message (str): The message content to summarize.

        Returns:
            str: The summarized message.
        """
        return await self.summarize_AI_message(message)