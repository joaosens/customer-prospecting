import os
import requests
import csv
import whois
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
api_key = os.getenv('API_KEY')

URL_API = "https://google.serper.dev/places"
profissao = 'Nutricionistas'
nome_csv = f"leads_{profissao.lower}_completo.csv"


# Estrutura de colunas do CSV
colunas = [
    "Posição", "Nome do Profissional", "Telefone", "Website Cadastrado",
    "Tempo de Existência do Site", "Status do Lead", "Análise Comercial",
    "Avaliação (Nota)", "Quantidade de Reviews", "Endereço"
]

# CORREÇÃO 1: Cria o arquivo e escreve o cabeçalho APENAS UMA VEZ no início
try:
    with open(nome_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(colunas)
except PermissionError:
    print(f"\n❌ ERRO DE PERMISSÃO: O arquivo '{nome_csv}' está aberto no Excel!")
    print("Por favor, feche a planilha e execute o script novamente.\n")
    exit()

# FUNÇÃO PARA EXTRAIR APENAS O DOMÍNIO PRINCIPAL
def extrair_dominio(url):
    if not url:
        return None
    url = url.lower().replace("http://", "").replace("https://", "")
    url = url.replace("www.", "").split("/")[0]
    return url

# FUNÇÃO PARA DESCOBRIR A IDADE DO SITE VIA WHOIS
def obter_idade_site(url_site):
    dominio = extrair_dominio(url_site)
    if not dominio:
        return "Sem site"

    plataformas_comuns = ["instagram.com", "facebook.com", "doctoralia.com.br", "dietbox.me", "mydoseapp.com", "linktr.ee"]
    if any(p in dominio for p in plataformas_comuns):
        return "N/A (Plataforma Terceirizada)"

    try:
        info_dominio = whois.whois(dominio)
        data_criacao = info_dominio.creation_date

        if isinstance(data_criacao, list):
            data_criacao = data_criacao[0]

        if data_criacao and isinstance(data_criacao, datetime):
            ano_criacao = data_criacao.year
            ano_atual = datetime.now().year
            idade_anos = ano_atual - ano_criacao

            if idade_anos == 0:
                return "Menos de 1 ano (Recente! 🆕)"
            return f"{idade_anos} ano(s) (Criado em {ano_criacao})"

        return "Não foi possível calcular"
    except Exception:
        return "Erro ao consultar idade"


pagina_atual = 1
total_leads = 0

headers = {
  'X-API-KEY': api_key,
  'Content-Type': 'application/json'
}

# CORREÇÃO 2: Loop real de paginação para varrer TODOS os nutricionistas
while True:
    # O payload PRECISA ser gerado aqui dentro para atualizar o número da página dinamicamente
    payload = {
      "q": f"{profissao}",
      "gl": "br",
      "location": "Curitiba, State of Parana, Brazil",
      "num": 20,              
      "page": pagina_atual  
    }

    try:
        print(f"\n📡 Conectando à API Serper e buscando clientes na página {pagina_atual}...")
        response = requests.post(URL_API, headers=headers, json=payload)
        response.raise_for_status()
        dados_api = response.json()

        places = dados_api.get("places", [])
        
        # Condição de parada: se a página vier vazia, terminamos
        if not places:
            print("\n🏁 O Google Maps não possui mais resultados. Varredura concluída!")
            break

        print(f"✅ Sucesso! {len(places)} estabelecimentos encontrados nesta página.")
        print("🕵️‍♂️ Analisando domínios e salvando dados...")

        # Abre em modo "a" (append) apenas para adicionar as linhas novas
        with open(nome_csv, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")

            for place in places:
                pos = place.get("position")
                nome = place.get("title")
                tel = place.get("phoneNumber", "Sem Telefone")
                site = place.get("website", "")
                nota = place.get("rating", "Sem nota")
                reviews = place.get("ratingCount", 0)
                endereco = place.get("address")

                tempo_site = obter_idade_site(site)

                site_lower = site.lower()
                if site == "":
                    status = "🔥 QUENTE DEMAIS!"
                    analise = "Não tem site. Oportunidade perfeita de venda de Landing Page."
                elif "instagram.com" in site_lower:
                    status = "🔥 QUENTE!"
                    analise = "Usa rede social no lugar de site profissional. Perde conversão."
                elif any(p in site_lower for p in ["doctoralia", "dietbox", "mydoseapp", "linktr"]):
                    status = "⚡ MORNO"
                    analise = "Depende de plataformas terceiras. Precisa de marca própria."
                else:
                    status = "❄️ Frio"
                    analise = f"Já tem site próprio estruturado ({tempo_site})."

                writer.writerow([pos, nome, tel, site if site else "Nenhum", tempo_site, status, analise, nota, reviews, endereco])
                total_leads += 1
                print(f"   ↳ 👤 [#{total_leads}] {nome[:25]}... -> [{status}]")

        # Incrementa para puxar a próxima página na próxima rodada do loop
        pagina_atual += 1
        time.sleep(1) # Evita spam de requisições rápidas

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Erro na requisição da API: {e}")
        break
    except PermissionError:
        print(f"\n❌ ERRO DE PERMISSÃO: Você abriu a planilha durante a execução! Feche-a.")
        break
    except Exception as e:
        print(f"\n❌ Ocorreu um erro geral no script: {e}")
        break

print(f"\n🚀 Prontinho! {total_leads} leads processados com sucesso no arquivo: '{nome_csv}'")
