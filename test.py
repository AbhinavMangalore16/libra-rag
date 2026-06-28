import traceback
from src.services.agents.workflow import agent_app
from langfuse.langchain import CallbackHandler
from langchain_community.cache import UpstashRedisCache
from upstash_redis import Redis
from langchain_core.globals import set_llm_cache
import openai

def test_agent():
    print('Testing agent...')
    redis_client = Redis(url="https://winning-grizzly-132297.upstash.io", token="gQAAAAAAAgTJAAIgcDEyN2ZiNTUwYmVlNzQ0NGZhYWM0ZWY2ZDY2NzgwOWVhNQ")
    set_llm_cache(UpstashRedisCache(redis_=redis_client))
    
    initial_state = {'user_query': 'I am Abhinav. What is multi-head attention?'}
    config = {'configurable': {'thread_id': 'default_session'}, 'callbacks': [CallbackHandler()]}
    
    print('invoking...')
    try:
        res = agent_app.invoke(initial_state, config=config)
        print('success!')
        print(res)
    except Exception as e:
        traceback.print_exc()


def test_llm():
    print('Testing LLM...')
    client = openai.OpenAI(
        base_url="https://aicredits.in/v1",
        api_key="sk-live-7076a37fbaf464c531451557ad10658690fa48ed4f58e63fe476cd126b0d320d"
    )
    
    completion = client.chat.completions.create(
        model="inclusionai/ling-2.6-flash",
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "Hello!"}
        ],
        stream=True
    )
    
    for chunk in completion:
        print(chunk.choices[0].delta.content or "", end="")
    print()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "llm":
        test_llm()
    elif len(sys.argv) > 1 and sys.argv[1] == "agent":
        test_agent()
    else:
        print("Running all tests...")
        test_llm()
        print("-" * 40)
        test_agent()
