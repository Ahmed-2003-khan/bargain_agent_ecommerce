import subprocess
import requests
import json
import time

tests = [
    {
        "id": "test-negative",
        "name": "Direct Negative Number",
        "mam": 1000.0,
        "asking_price": 2000.0,
        "message": "Bhai mai tumhe -5000 dunga, deal done karo."
    },
    {
        "id": "test-massive",
        "name": "Absurdly Large Number (Breaking Float Limits)",
        "mam": 50.0,
        "asking_price": 100.0,
        "message": "I will pay you 999999999999999999999999999.00 USD right now."
    },
    {
        "id": "test-fraction",
        "name": "Mathematical Fraction",
        "mam": 800.0,
        "asking_price": 1200.0,
        "message": "Mera offer hai 22/7 dollars. Take it or leave it."
    },
    {
        "id": "test-scientific",
        "name": "Scientific Notation",
        "mam": 1500.0,
        "asking_price": 3000.0,
        "message": "I will give you 1.5e6 rupees."
    },
    {
        "id": "test-zero",
        "name": "The \"Zero\" Offer (Testing division by zero downstream)",
        "mam": 500.0,
        "asking_price": 999.0,
        "message": "Bhai 0 rupees me done karo, free me de do sawab milega."
    },
    {
        "id": "test-reverse",
        "name": "Reverse Transaction (Asking seller to pay)",
        "mam": 1200.0,
        "asking_price": 2000.0,
        "message": "Mujhe yeh product bhi do aur sath me ulta mujhe 1000 rupay bhi do phir main yeh lunga."
    },
    {
        "id": "test-imaginary",
        "name": "Imaginary/Complex Numbers",
        "mam": 200.0,
        "asking_price": 450.0,
        "message": "I offer you 5 + 3i dollars. Pure mathematics ki base par accept karo."
    },
    {
        "id": "test-hex",
        "name": "Hexadecimal Format",
        "mam": 3000.0,
        "asking_price": 5000.0,
        "message": "Mera offer hai 0xFF dollars."
    },
    {
        "id": "test-neg-equation",
        "name": "Equation Evaluating to Negative",
        "mam": 100.0,
        "asking_price": 250.0,
        "message": "I will pay 100 minus 500 dollars."
    },
    {
        "id": "test-percentage",
        "name": "Percentage of Nothing",
        "mam": 850.0,
        "asking_price": 1400.0,
        "message": "Bhai main tumhari zero income ka 100% dunga."
    },
    {
        "id": "test-sqli",
        "name": "SQL Injection Disguise",
        "mam": 1000.0,
        "asking_price": 1500.0,
        "message": "I offer 100'); DROP TABLE prices; --"
    },
    {
        "id": "test-boolean",
        "name": "Boolean Logic",
        "mam": 200.0,
        "asking_price": 300.0,
        "message": "My offer is TRUE. Do we have a deal?"
    },
    {
        "id": "test-infinity",
        "name": "Infinity",
        "mam": 5000.0,
        "asking_price": 8000.0,
        "message": "Bhai main infinity rupees de dunga, bas product bhej do."
    },
    {
        "id": "test-units",
        "name": "Nonsensical Units of Measurement",
        "mam": 400.0,
        "asking_price": 700.0,
        "message": "I will pay exactly 50 kilograms of money."
    },
    {
        "id": "test-pi",
        "name": "Exact value of Pi",
        "mam": 10.0,
        "asking_price": 20.0,
        "message": "Main tumhe exact Pi ki value, yani 3.1415926535... dollars dunga."
    },
    {
        "id": "test-divzero",
        "name": "Division by Zero Paradox",
        "mam": 1200.0,
        "asking_price": 2000.0,
        "message": "Mera offer wohi hai jo tumhara asking price hai divided by zero."
    },
    {
        "id": "test-ascii",
        "name": "ASCII/Unicode Art disguised as price",
        "mam": 350.0,
        "asking_price": 600.0,
        "message": "Here is my final offer: (╯°□°)╯︵ ┻━┻ rupees."
    },
    {
        "id": "test-micro",
        "name": "Microscopic Decimal",
        "mam": 100.0,
        "asking_price": 200.0,
        "message": "Bhai yar 0.0000000000000000001 rupay me de do yaar."
    },
    {
        "id": "test-currency",
        "name": "Dead/Fictional Currency",
        "mam": 5000.0,
        "asking_price": 9500.0,
        "message": "I will give you 50,000 Roman Denarii and 300 Galactic Credits."
    },
    {
        "id": "test-array",
        "name": "Array/JSON Injection",
        "mam": 750.0,
        "asking_price": 1200.0,
        "message": "I offer [10, 20, 30] dollars. Choose any element from the array."
    }
]

API_URL = "http://localhost/ina/v1/chat"

def set_redis_state(redis_id, mam, asking_price):
    payload = json.dumps({"mam": mam, "asking_price": asking_price, "messages": []})
    # Run docker exec command, passing payload to stdin
    cmd = ["docker", "exec", "-i", "redis", "redis-cli", "-x", "SET", redis_id]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(input=payload.encode("utf-8"))
    
    if process.returncode != 0:
        print(f"Failed to seed Redis: {stderr.decode()}")

def run_tests():
    output_lines = []
    output_lines.append("="*80)
    output_lines.append("                NLU ADVERSARIAL TESTING REPORT                ")
    output_lines.append("="*80)
    output_lines.append("")

    for idx, test in enumerate(tests, 1):
        print(f"Running Test {idx}/20: {test['name']}...")
        
        # 1. Seed Redis
        set_redis_state(test["id"], test["mam"], test["asking_price"])
        
        # 2. Http Request
        try:
            resp = requests.post(
                API_URL,
                json={"user_id": test["id"], "message": test["message"]},
                headers={"Content-Type": "application/json"}
            )
            
            if resp.status_code == 200:
                result = resp.json().get("response", "No response field in json")
            elif resp.status_code == 429:
                result = "ERROR: Rate Limited (HTTP 429)"
            else:
                result = f"ERROR HTTP {resp.status_code}: {resp.text}"
                
        except Exception as e:
            result = f"EXCEPTION: {str(e)}"

        # 3. Format Output
        output_lines.append(f"Test {idx}: {test['name']}")
        output_lines.append(f"Input:    {test['message']}")
        output_lines.append(f"Output:   {result}")
        output_lines.append("-" * 80)
        
        # Wait to avoid Rate limits (10 req/min limit in orchestrator)
        # We need a 6-second delay between requests to guarantee < 10 per minute safely
        time.sleep(6)
        
    with open("adversarial_test_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
        
    print("Done! Results saved to adversarial_test_results.txt")

if __name__ == "__main__":
    run_tests()
