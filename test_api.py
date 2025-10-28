"""
Script de teste automatizado para Disease Predictor API
Execute este script para validar se a API está funcionando corretamente
"""

import requests
import json
import time
from colorama import init, Fore, Style

# Inicializar colorama para output colorido
init(autoreset=True)

BASE_URL = "http://localhost:5000"

def print_header(text):
    """Imprime cabeçalho formatado"""
    print("\n" + "="*60)
    print(f"{Fore.CYAN}{Style.BRIGHT}{text}")
    print("="*60)

def print_success(text):
    """Imprime mensagem de sucesso"""
    print(f"{Fore.GREEN}✅ {text}")

def print_error(text):
    """Imprime mensagem de erro"""
    print(f"{Fore.RED}❌ {text}")

def print_warning(text):
    """Imprime mensagem de aviso"""
    print(f"{Fore.YELLOW}⚠️  {text}")

def print_info(text):
    """Imprime informação"""
    print(f"{Fore.BLUE}ℹ️  {text}")

def test_health_check():
    """Testa o endpoint de health check"""
    print_header("Teste 1: Health Check")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Status: {data['status']}")
            print_info(f"Total de sintomas: {data['total_symptoms']}")
            print_info(f"Total de categorias: {data['total_categories']}")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Não foi possível conectar ao servidor!")
        print_warning("Certifique-se de que o servidor Flask está rodando (python app.py)")
        return False
    except Exception as e:
        print_error(f"Erro: {str(e)}")
        return False

def test_get_symptoms():
    """Testa o endpoint de listagem de sintomas"""
    print_header("Teste 2: Listar Sintomas")
    try:
        response = requests.get(f"{BASE_URL}/api/symptoms", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Total de sintomas: {data['total']}")
            print_info(f"Primeiros 5 sintomas: {', '.join(data['symptoms'][:5])}")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Erro: {str(e)}")
        return False

def test_search_symptoms():
    """Testa a busca de sintomas"""
    print_header("Teste 3: Buscar Sintomas")
    search_terms = ["pain", "cough", "fever"]
    
    for term in search_terms:
        try:
            response = requests.get(
                f"{BASE_URL}/api/symptoms",
                params={"search": term},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                print_success(f"Busca por '{term}': {data['total']} sintomas encontrados")
            else:
                print_error(f"Busca por '{term}' falhou")
                return False
        except Exception as e:
            print_error(f"Erro ao buscar '{term}': {str(e)}")
            return False
    
    return True

def test_get_categories():
    """Testa o endpoint de categorias"""
    print_header("Teste 4: Listar Categorias")
    try:
        response = requests.get(f"{BASE_URL}/api/categories", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Total de categorias: {data['total']}")
            print_info(f"Categorias: {', '.join(data['categories'][:5])}...")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Erro: {str(e)}")
        return False

def test_prediction(test_name, symptoms, expected_category=None):
    """Testa uma predição específica"""
    print_header(f"Teste de Predição: {test_name}")
    
    payload = {
        "symptoms": symptoms,
        "top_k": 5
    }
    
    print_info(f"Sintomas testados: {', '.join([k for k, v in symptoms.items() if v == 1])}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/predict",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data['success']:
                print_success("Predição realizada com sucesso!")
                print_info(f"Sintomas analisados: {data['metadata']['total_symptoms_analyzed']}")
                
                print(f"\n{Fore.YELLOW}Top 5 Predições:")
                for i, pred in enumerate(data['predictions'], 1):
                    confidence_color = Fore.GREEN if pred['confidence'] == 'High' else \
                                     Fore.YELLOW if pred['confidence'] == 'Medium' else Fore.RED
                    print(f"  {i}. {pred['category']}: {pred['percentage']} "
                          f"{confidence_color}[{pred['confidence']}]")
                
                if expected_category:
                    top_pred = data['predictions'][0]['category']
                    if expected_category.lower() in top_pred.lower():
                        print_success(f"✓ Categoria esperada '{expected_category}' está no topo!")
                    else:
                        print_warning(f"Categoria esperada era '{expected_category}', "
                                    f"mas o modelo previu '{top_pred}'")
                
                if data['metadata']['symptoms_not_found']:
                    print_warning(f"Sintomas não encontrados: "
                                f"{', '.join(data['metadata']['symptoms_not_found'])}")
                
                return True
            else:
                print_error(f"Erro na predição: {data.get('error', 'Unknown')}")
                return False
        else:
            print_error(f"Status code: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Erro: {str(e)}")
        return False

def test_invalid_requests():
    """Testa requisições inválidas"""
    print_header("Teste 5: Validação de Erros")
    
    tests = [
        {
            "name": "Sem campo symptoms",
            "payload": {"top_k": 5},
            "expected_status": 400
        },
        {
            "name": "Symptoms vazio",
            "payload": {"symptoms": {}},
            "expected_status": 400
        },
        {
            "name": "Symptoms não é dict",
            "payload": {"symptoms": "invalid"},
            "expected_status": 400
        }
    ]
    
    for test in tests:
        try:
            response = requests.post(
                f"{BASE_URL}/api/predict",
                json=test["payload"],
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code == test["expected_status"]:
                print_success(f"{test['name']}: Erro tratado corretamente (status {response.status_code})")
            else:
                print_error(f"{test['name']}: Status esperado {test['expected_status']}, "
                          f"recebido {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Erro no teste '{test['name']}': {str(e)}")
            return False
    
    return True

def test_diseases_by_category():
    """Testa o endpoint de doenças por categoria"""
    print_header("Teste 6: Doenças por Categoria")
    
    test_categories = ["Respiratory", "Cardiovascular", "Gastrointestinal"]
    
    for category in test_categories:
        try:
            response = requests.get(
                f"{BASE_URL}/api/diseases-by-category/{category}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"{category}: {data['total_diseases']} doenças")
            else:
                print_error(f"Falha ao obter doenças de {category}")
                return False
        except Exception as e:
            print_error(f"Erro: {str(e)}")
            return False
    
    # Testar categoria inválida
    try:
        response = requests.get(
            f"{BASE_URL}/api/diseases-by-category/InvalidCategory",
            timeout=5
        )
        if response.status_code == 404:
            print_success("Categoria inválida retornou 404 corretamente")
        else:
            print_error(f"Categoria inválida deveria retornar 404, retornou {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Erro: {str(e)}")
        return False
    
    return True

def run_all_tests():
    """Executa todos os testes"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     DISEASE PREDICTOR API - SUITE DE TESTES AUTOMÁTICOS   ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(Style.RESET_ALL)
    
    start_time = time.time()
    results = []
    
    # Lista de testes
    tests = [
        ("Health Check", test_health_check),
        ("Listar Sintomas", test_get_symptoms),
        ("Buscar Sintomas", test_search_symptoms),
        ("Listar Categorias", test_get_categories),
        ("Validação de Erros", test_invalid_requests),
        ("Doenças por Categoria", test_diseases_by_category),
    ]
    
    # Executar testes básicos
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
        time.sleep(0.5)  # Pequena pausa entre testes
    
    # Testes de predição
    prediction_tests = [
        ("Sintomas Respiratórios", {
            "cough": 1,
            "shortness of breath": 1,
            "fever": 1,
            "chest tightness": 1
        }, "Respiratory"),
        
        ("Sintomas Cardíacos", {
            "sharp chest pain": 1,
            "palpitations": 1,
            "dizziness": 1,
            "irregular heartbeat": 1
        }, "Cardiovascular"),
        
        ("Sintomas Gastrointestinais", {
            "sharp abdominal pain": 1,
            "nausea": 1,
            "vomiting": 1,
            "diarrhea": 1
        }, "Gastrointestinal"),
        
        ("Sintomas Neurológicos", {
            "headache": 1,
            "dizziness": 1,
            "weakness": 1,
            "abnormal involuntary movements": 1
        }, "Neurological"),
        
        ("Sintomas Mistos", {
            "fever": 1,
            "cough": 1,
            "headache": 1,
            "fatigue": 1
        }, None)
    ]
    
    for test_name, symptoms, expected in prediction_tests:
        result = test_prediction(test_name, symptoms, expected)
        results.append((f"Predição: {test_name}", result))
        time.sleep(0.5)
    
    # Resumo dos resultados
    print_header("RESUMO DOS TESTES")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")
    
    elapsed_time = time.time() - start_time
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Style.BRIGHT}Total: {passed}/{total} testes passaram")
    print(f"Tempo de execução: {elapsed_time:.2f} segundos")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    
    if passed == total:
        print(f"{Fore.GREEN}{Style.BRIGHT}🎉 TODOS OS TESTES PASSARAM! 🎉{Style.RESET_ALL}\n")
        return True
    else:
        print(f"{Fore.RED}{Style.BRIGHT}⚠️  ALGUNS TESTES FALHARAM ⚠️{Style.RESET_ALL}\n")
        return False

if __name__ == "__main__":
    print(f"{Fore.YELLOW}")
    print("Certifique-se de que o servidor Flask está rodando:")
    print("  python app.py")
    print(f"{Style.RESET_ALL}")
    
    input("Pressione ENTER para iniciar os testes...")
    
    success = run_all_tests()
    
    exit(0 if success else 1)