import json
from routes.llm_service import call_gemini_model, SECONDARY_MODEL

# Forçamos falha sempre que tentar o primário
def call_primary_fail(prompt: str, max_output_tokens: int = 1000):
    raise Exception("Forçando falha no modelo primário (teste)")

def test_fallback():
    prompt = "Teste rápido de fallback RPG"
    print("\n=== Iniciando teste de fallback ===")

    # 1. Forçar falha no primário
    try:
        resposta = call_primary_fail(prompt)
        print("✅ Isso não deveria aparecer (modelo primário respondeu!)")
    except Exception as e1:
        print("⚠️ Modelo primário falhou de propósito:", e1)

    # 2. Tentar secundário
    try:
        resposta = call_gemini_model(prompt, SECONDARY_MODEL)
        print(f"✅ Resposta do modelo secundário: {SECONDARY_MODEL}")
        print("Saída (truncada):", resposta[:200], "...")
        return
    except Exception as e2:
        print(f"⚠️ Modelo secundário {SECONDARY_MODEL} falhou:", e2)

    # 3. Se tudo falhar → JSON fixo
    print("❌ Todos os modelos falharam, usando narrativa padrão")
    resposta = {
        "narrativa": ["O encontro começa..."],
        "escolhas": ["Atacar", "Defender", "Usar Item"],
        "status": {},
        "turn_result": {}
    }
    print("Saída fixa:", json.dumps(resposta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    test_fallback()
