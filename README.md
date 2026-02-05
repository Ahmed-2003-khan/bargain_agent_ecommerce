# INA Orchestrator


# http://127.0.0.1:8000/docs for browser testing
# http://localhost:8002/docs NLU-test
# http://localhost:8001/docs Strategy-engine test

# for initializing session: 
# docker exec -it redis redis-cli SET session:Ashna '{\"messages\": []}'

# Test on powershell directly:
## Invoke-RestMethod -Method POST `
#  -Uri "http://localhost:8000/ina/v1/chat" `
#  -Body '{"user_id":"Ashna","message":"this price is way too high, it's honestly unfair"}' `
#  -ContentType "application/json" 


# Correct session initilization:
# '{"messages":[]}' | docker exec -i redis redis-cli -x SET session:Ashna

