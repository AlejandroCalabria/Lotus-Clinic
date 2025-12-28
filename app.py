import gdown
import os
import pickle
import json

# ========== CONFIGURAÇÃO DOS ARQUIVOS DO GOOGLE DRIVE ==========
ARQUIVOS_MODELO = {
    'disease_classifier_model.pkl': '1uiqemJi_f7YDbzCootmoUuTfSlC91C-a',
    'disease_model.pkl': '1sNe3V6ctHYBvp96pbsiJ2WYIkvGqzsC_',
    'label_encoder.pkl': '1PAoCPOM7vHv4ca8FriXx3irZLLVV3kj0',
    'symptom_columns.pkl': '1wIqMCEhK7z1LA_oODnEa5njSYlfMoRfr'
}

def download_model_from_drive():
    """Baixa todos os arquivos necessários do Google Drive"""
    print("\n" + "="*70)
    print("📦 VERIFICANDO ARQUIVOS DE MODELO (GOOGLE DRIVE)")
    print("="*70)
    
    for arquivo, file_id in ARQUIVOS_MODELO.items():
        if not os.path.exists(arquivo):
            print(f"\n📥 Baixando {arquivo}...")
            
            url = f'https://drive.google.com/uc?id={file_id}'
            
            try:
                gdown.download(url, arquivo, quiet=False)
                
                if os.path.exists(arquivo):
                    size_mb = os.path.getsize(arquivo) / (1024 * 1024)
                    print(f"✅ {arquivo} baixado com sucesso! ({size_mb:.2f} MB)")
                else:
                    raise Exception(f"Arquivo {arquivo} não foi criado após download")
                    
            except Exception as e:
                print(f"❌ ERRO CRÍTICO ao baixar {arquivo}: {e}")
                print(f"   ID usado: {file_id}")
                print(f"   URL: {url}")
                raise Exception(f"Falha ao baixar arquivo essencial: {arquivo}")
        else:
            size_mb = os.path.getsize(arquivo) / (1024 * 1024)
            print(f"✅ {arquivo} já existe ({size_mb:.2f} MB)")
    
    print("\n" + "="*70)
    print("🎉 TODOS OS ARQUIVOS CARREGADOS COM SUCESSO!")
    print("="*70 + "\n")

# ========== BAIXAR MODELOS ANTES DE TUDO ==========
download_model_from_drive()

from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for
from flask_cors import CORS
import pandas as pd
from datetime import datetime
import logging
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
import hashlib
import requests
from functools import wraps

# Mapeamento de categorias IA para especialidades médicas
CATEGORIA_PARA_ESPECIALIDADE = {
    'Respiratory': 'Respiratório',
    'Cardiovascular': 'Cardiologista',
    'Gastrointestinal': 'Gastrointestinal',
    'Neurological': 'Neurologia',
    'Musculoskeletal': 'Ortopedia',
    'Dermatological': 'Dermatologia',
    'Endocrine_Metabolic': 'Endocrinologia',
    'Renal_Urological': 'Urologia',
    'Gynecological_Obstetric': 'Ginecologia',
    'Ophthalmological': 'Oftalmologia',
    'ENT': 'Otorrinolaringologia',
    'Hematological_Oncological': 'Hematologia',
    'Psychiatric': 'Psiquiatria',
    'Other': 'Clínico Geral'
}

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_super_segura_aqui_2024'  # Mude isso em produção
CORS(app)

# Configurações de upload
UPLOAD_FOLDER = 'static/uploads/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max

# Criar pasta de uploads se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ========== BANCO DE DADOS ==========
import mysql.connector
from mysql.connector import Error
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()  # IMPORTANTÍSSIMO
# Debug de configuração do banco
use_local = os.getenv("USE_LOCAL_DB", "False").lower() == "true"

if use_local:
    print("=" * 70)
    print("🔧 MODO: BANCO DE DADOS LOCAL (XAMPP)")
    print("=" * 70)
    print(f"HOST: {os.getenv('LOCAL_DB_HOST', '127.0.0.1')}")
    print(f"PORT: {os.getenv('LOCAL_DB_PORT', '3306')}")
    print(f"USER: {os.getenv('LOCAL_DB_USER', 'root')}")
    print(f"DB: {os.getenv('LOCAL_DB_NAME', 'railway')}")
    print("=" * 70)
else:
    print("=" * 70)
    print("☁️ MODO: BANCO DE DADOS RAILWAY (NUVEM)")
    print("=" * 70)
    url = urlparse(os.getenv("MYSQL_PUBLIC_URL"))
    print(f"HOST: {url.hostname}:{url.port}")
    print(f"USER: {url.username}")
    print(f"PASS: {url.password[:5]}...")
    print(f"DB: {url.path[1:]}")
    print("=" * 70)
url = urlparse(os.getenv("MYSQL_PUBLIC_URL"))
print("DEBUG HOST:", url.hostname, url.port)

def get_db_connection():
    """Conectar ao banco de dados (local ou Railway)"""
    try:
        # Verificar qual banco usar
        use_local = os.getenv("USE_LOCAL_DB", "False").lower() == "true"
        
        if use_local:
            # ========== BANCO LOCAL (XAMPP) ==========
            print("🔌 Conectando ao banco LOCAL (XAMPP)...")
            connection = mysql.connector.connect(
                host=os.getenv("LOCAL_DB_HOST", "127.0.0.1"),
                port=int(os.getenv("LOCAL_DB_PORT", 3306)),
                user=os.getenv("LOCAL_DB_USER", "root"),
                password=os.getenv("LOCAL_DB_PASSWORD", ""),
                database=os.getenv("LOCAL_DB_NAME", "railway"),
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
        else:
            # ========== BANCO RAILWAY (NUVEM) ==========
            print("☁️ Conectando ao banco RAILWAY (nuvem)...")
            url = urlparse(os.getenv("MYSQL_PUBLIC_URL"))
            connection = mysql.connector.connect(
                host=url.hostname,
                port=url.port,
                user=url.username,
                password=url.password,
                database=url.path[1:],
                ssl_disabled=False,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )

        if connection.is_connected():
            db_info = connection.get_server_info()
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            db_name = cursor.fetchone()[0]
            cursor.close()
            
            tipo_banco = "LOCAL (XAMPP)" if use_local else "RAILWAY (Nuvem)"
            print(f"✅ Conectado ao MySQL {tipo_banco}")
            print(f"   Versão do servidor: {db_info}")
            print(f"   Database ativa: {db_name}")
            
            return connection
            
    except Error as e:
        tipo_banco = "LOCAL" if use_local else "RAILWAY"
        print(f"❌ Erro ao conectar ao MySQL {tipo_banco}: {e}")
        return None

def hash_senha(senha):
    """Gera hash SHA256 da senha"""
    return hashlib.sha256(senha.encode()).hexdigest()

import secrets
import string

def gerar_senha_forte(tamanho=12):
    """Gera uma senha forte aleatória"""
    caracteres = string.ascii_letters + string.digits + "!@#$%&*"
    senha = ''.join(secrets.choice(caracteres) for _ in range(tamanho))
    # Garantir que tem pelo menos 1 maiúscula, 1 minúscula, 1 número e 1 especial
    if (any(c.isupper() for c in senha) and 
        any(c.islower() for c in senha) and 
        any(c.isdigit() for c in senha) and 
        any(c in "!@#$%&*" for c in senha)):
        return senha
    else:
        return gerar_senha_forte(tamanho)  # Recursão se não atender critérios

def allowed_file(filename):
    """Verifica se o arquivo é permitido"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    """Decorator para proteger rotas que precisam de login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Login necessário'}), 401
        return f(*args, **kwargs)
    return decorated_function


TRADUCAO_SINTOMAS = {
    # Sintomas básicos (já existentes)
    'cough': 'tosse',
    'fever': 'febre',
    'headache': 'dor de cabeça',
    'shortness of breath': 'falta de ar',
    'chest tightness': 'aperto no peito',
    'nausea': 'náusea',
    'vomiting': 'vômito',
    'diarrhea': 'diarreia',
    'sharp abdominal pain': 'dor abdominal aguda',
    'sharp chest pain': 'dor aguda no peito',
    'palpitations': 'palpitações',
    'dizziness': 'tontura',
    'fatigue': 'fadiga',
    'weakness': 'fraqueza',
    'back pain': 'dor nas costas',
    'muscle pain': 'dor muscular',
    'joint pain': 'dor nas articulações',
    'sore throat': 'dor de garganta',
    'runny nose': 'nariz escorrendo',
    'nasal congestion': 'congestão nasal',
    'sweating': 'sudorese',
    'chills': 'calafrios',
    'loss of appetite': 'perda de apetite',
    'weight loss': 'perda de peso',
    'difficulty breathing': 'dificuldade para respirar',
    'wheezing': 'chiado no peito',
    'rapid breathing': 'respiração rápida',
    'irregular heartbeat': 'batimento cardíaco irregular',
    'arm pain': 'dor no braço',
    'jaw pain': 'dor na mandíbula',
    'anxiety and nervousness': 'ansiedade e nervosismo',
    'depression': 'depressão',
    'insomnia': 'insônia',
    'skin rash': 'erupção cutânea',
    'itching of skin': 'coceira na pele',
    'painful urination': 'dor ao urinar',
    'frequent urination': 'micção frequente',
    'blood in urine': 'sangue na urina',
    'blurry vision': 'visão turva',
    'decreased vision': 'visão diminuída',
    'sensitivity to light': 'sensibilidade à luz',
    
    # Traduções adicionais do arquivo traducoes_extras.py
    'coughing up sputum': 'tosse com catarro',
    'hemoptysis': 'tosse com sangue',
    'apnea': 'parada respiratória',
    'rapid heart rate': 'frequência cardíaca acelerada',
    'low blood pressure': 'pressão baixa',
    'high blood pressure': 'pressão alta',
    'orthostatic hypotension': 'tontura ao levantar',
    'syncope': 'desmaio',
    'burning abdominal pain': 'dor abdominal em queimação',
    'lower abdominal pain': 'dor no baixo ventre',
    'upper abdominal pain': 'dor na parte superior do abdômen',
    'heartburn': 'azia',
    'regurgitation': 'refluxo',
    'constipation': 'constipação',
    'bloating': 'inchaço abdominal',
    'flatulence': 'gases',
    'bloody stool': 'sangue nas fezes',
    'black stool': 'fezes escuras',
    'difficulty speaking': 'dificuldade para falar',
    'abnormal involuntary movements': 'movimentos involuntários',
    'disturbance of memory': 'problema de memória',
    'problems with movement': 'problemas de movimento',
    'loss of sensation': 'perda de sensação',
    'numbness': 'dormência',
    'tingling': 'formigamento',
    'seizures': 'convulsões',
    'confusion': 'confusão mental',
    'loss of consciousness': 'perda de consciência',
    'tremor': 'tremor',
    'vertigo': 'vertigem',
    'neck pain': 'dor no pescoço',
    'shoulder pain': 'dor no ombro',
    'elbow pain': 'dor no cotovelo',
    'wrist pain': 'dor no pulso',
    'hand pain': 'dor na mão',
    'finger pain': 'dor no dedo',
    'hip pain': 'dor no quadril',
    'knee pain': 'dor no joelho',
    'ankle pain': 'dor no tornozelo',
    'foot pain': 'dor no pé',
    'muscle stiffness': 'rigidez muscular',
    'muscle weakness': 'fraqueza muscular',
    'muscle cramps': 'cãibras musculares',
    'joint swelling': 'inchaço nas articulações',
    'bones are painful': 'dor nos ossos',
    'skin lesion': 'lesão na pele',
    'abnormal appearing skin': 'pele com aparência anormal',
    'skin swelling': 'inchaço na pele',
    'skin dryness': 'pele seca',
    'dry skin': 'pele seca',
    'skin growth': 'crescimento na pele',
    'warts': 'verrugas',
    'moles': 'pintas',
    'acne': 'acne',
    'hives': 'urticária',
    'eczema': 'eczema',
    'bruising': 'hematomas',
    'pallor': 'palidez',
    'jaundice': 'icterícia',
    'flushing': 'rubor',
    'double vision': 'visão dupla',
    'spots or clouds in vision': 'manchas na visão',
    'eye pain': 'dor nos olhos',
    'eye redness': 'olhos vermelhos',
    'itchiness of eye': 'coceira nos olhos',
    'watery eyes': 'olhos lacrimejantes',
    'dry eyes': 'olhos secos',
    'eyelid swelling': 'inchaço nas pálpebras',
    'discharge from eye': 'secreção nos olhos',
    'floaters': 'moscas volantes',
    'difficulty in swallowing': 'dificuldade para engolir',
    'painful swallowing': 'dor ao engolir',
    'hoarse voice': 'rouquidão',
    'loss of voice': 'perda de voz',
    'nose bleeding': 'sangramento nasal',
    'loss of smell': 'perda de olfato',
    'loss of taste': 'perda de paladar',
    'ear pain': 'dor de ouvido',
    'ringing in ear': 'zumbido no ouvido',
    'decreased hearing': 'diminuição da audição',
    'ear discharge': 'secreção no ouvido',
    'plugged feeling in ear': 'ouvido entupido',
    'decreased urine output': 'diminuição da urina',
    'increased urination': 'aumento da micção',
    'difficulty urinating': 'dificuldade para urinar',
    'urinary hesitancy': 'hesitação urinária',
    'urinary urgency': 'urgência urinária',
    'incontinence': 'incontinência',
    'cloudy urine': 'urina turva',
    'dark urine': 'urina escura',
    'foul smelling urine': 'urina com mau cheiro',
    'night sweats': 'suores noturnos',
    'lethargy': 'letargia',
    'malaise': 'mal-estar',
    'weight gain': 'ganho de peso',
    'increased appetite': 'aumento de apetite',
    'increased thirst': 'aumento da sede',
    'dehydration': 'desidratação',
    'edema': 'edema',
    'swelling': 'inchaço',
    'lymph nodes enlargement': 'gânglios aumentados',
    'excessive anger': 'raiva excessiva',
    'feeling ill': 'sentir-se doente',
    'lack of motivation': 'falta de motivação',
    'difficulty concentrating': 'dificuldade de concentração',
    'memory loss': 'perda de memória',
    'mood swings': 'mudanças de humor',
    'irritability': 'irritabilidade',
    'restlessness': 'inquietação',
    'hallucinations': 'alucinações',
    'delusions': 'delírios',
    'paranoia': 'paranoia',
    'vaginal discharge': 'corrimento vaginal',
    'vaginal itching': 'coceira vaginal',
    'vaginal bleeding': 'sangramento vaginal',
    'painful menstruation': 'menstruação dolorosa',
    'irregular menstruation': 'menstruação irregular',
    'absence of menstruation': 'ausência de menstruação',
    'breast pain': 'dor nas mamas',
    'breast lump': 'nódulo na mama',
    'nipple discharge': 'secreção no mamilo',
    'pelvic pain': 'dor pélvica',
    'erectile dysfunction': 'disfunção erétil',
    'testicular pain': 'dor testicular',
    'scrotal swelling': 'inchaço escrotal',
    'allergic reaction': 'reação alérgica',
    'swollen lymph nodes': 'gânglios inchados',
    'bleeding': 'sangramento',
    'lumps': 'caroços',
    'discharge': 'secreção',
    'burning sensation': 'sensação de queimação',
    'pins and needles': 'formigamento',
    'hot flashes': 'ondas de calor',
    'cold intolerance': 'intolerância ao frio',
    'heat intolerance': 'intolerância ao calor',
    'feeling faint': 'sensação de desmaio',
    'lightheadedness': 'cabeça leve',
    'unsteady gait': 'marcha instável',
    'difficulty with walking': 'dificuldade para andar',
    'falling': 'quedas',
    'clumsiness': 'descoordenação',
    
    # Sintomas faltantes (não estavam em nenhum dos arquivos anteriores)
    'pus in sputum': 'pus no catarro',
    'symptoms of the scrotum and testes': 'sintomas no escroto e testículos',
    'swelling of scrotum': 'inchaço no escroto',
    'pus draining from ear': 'pus saindo do ouvido',
    'mass in scrotum': 'massa no escroto',
    'white discharge from eye': 'secreção branca no olho',
    'irritable infant': 'bebê irritado',
    'abusing alcohol': 'abuso de álcool',
    'fainting': 'desmaio',
    'hostile behavior': 'comportamento hostil',
    'drug abuse': 'abuso de drogas',
    'vaginal dryness': 'secura vaginal',
    'pain during intercourse': 'dor durante relação sexual',
    'involuntary urination': 'micção involuntária',
    'hand or finger pain': 'dor na mão ou dedo',
    'hand or finger swelling': 'inchaço na mão ou dedo',
    'arm stiffness or tightness': 'rigidez no braço',
    'arm swelling': 'inchaço no braço',
    'hand or finger stiffness or tightness': 'rigidez na mão ou dedo',
    'wrist stiffness or tightness': 'rigidez no pulso',
    'lip swelling': 'inchaço no lábio',
    'toothache': 'dor de dente',
    'acne or pimples': 'acne ou espinhas',
    'dry lips': 'lábios secos',
    'facial pain': 'dor facial',
    'mouth ulcer': 'úlcera na boca',
    'eye deviation': 'desvio ocular',
    'diminished vision': 'visão diminuída',
    'cross-eyed': 'vesgo',
    'symptoms of eye': 'sintomas oculares',
    'pain in eye': 'dor no olho',
    'eye moves abnormally': 'olho move-se anormalmente',
    'abnormal movement of eyelid': 'movimento anormal da pálpebra',
    'foreign body sensation in eye': 'sensação de corpo estranho no olho',
    'irregular appearing scalp': 'couro cabeludo com aparência irregular',
    'low back pain': 'dor lombar',
    'pain of the anus': 'dor no ânus',
    'pain during pregnancy': 'dor durante gravidez',
    'impotence': 'impotência',
    'infant spitting up': 'bebê regurgitando',
    'vomiting blood': 'vômito com sangue',
    'symptoms of infants': 'sintomas em bebês',
    'peripheral edema': 'edema periférico',
    'neck mass': 'massa no pescoço',
    'jaw swelling': 'inchaço na mandíbula',
    'mouth dryness': 'boca seca',
    'neck swelling': 'inchaço no pescoço',
    'foot or toe pain': 'dor no pé ou dedo',
    'bowlegged or knock-kneed': 'pernas arqueadas ou joelhos juntos',
    'knee weakness': 'fraqueza no joelho',
    'knee swelling': 'inchaço no joelho',
    'skin moles': 'pintas na pele',
    'knee lump or mass': 'massa ou caroço no joelho',
    'knee stiffness or tightness': 'rigidez no joelho',
    'leg swelling': 'inchaço na perna',
    'foot or toe swelling': 'inchaço no pé ou dedo',
    'smoking problems': 'problemas relacionados ao fumo',
    'infant feeding problem': 'problema de alimentação do bebê',
    'recent weight loss': 'perda de peso recente',
    'problems with shape or size of breast': 'problemas com formato ou tamanho da mama',
    'underweight': 'abaixo do peso',
    'difficulty eating': 'dificuldade para comer',
    'scanty menstrual flow': 'fluxo menstrual escasso',
    'vaginal pain': 'dor vaginal',
    'vaginal redness': 'vermelhidão vaginal',
    'vulvar irritation': 'irritação vulvar',
    'decreased heart rate': 'frequência cardíaca diminuída',
    'increased heart rate': 'frequência cardíaca aumentada',
    'bleeding or discharge from nipple': 'sangramento ou secreção no mamilo',
    'itchy ear(s)': 'coceira na(s) orelha(s)',
    'frontal headache': 'dor de cabeça frontal',
    'fluid in ear': 'líquido no ouvido',
    'neck stiffness or tightness': 'rigidez no pescoço',
    'lacrimation': 'lacrimejamento',
    'blindness': 'cegueira',
    'eye burns or stings': 'olho arde ou queima',
    'itchy eyelid': 'pálpebra com coceira',
    'feeling cold': 'sensação de frio',
    'decreased appetite': 'diminuição do apetite',
    'excessive appetite': 'apetite excessivo',
    'focal weakness': 'fraqueza focal',
    'slurring words': 'fala arrastada',
    'symptoms of the face': 'sintomas na face',
    'paresthesia': 'parestesia',
    'side pain': 'dor lateral',
    'shoulder stiffness or tightness': 'rigidez no ombro',
    'shoulder weakness': 'fraqueza no ombro',
    'arm cramps or spasms': 'cãibras ou espasmos no braço',
    'shoulder swelling': 'inchaço no ombro',
    'tongue lesions': 'lesões na língua',
    'leg cramps or spasms': 'cãibras ou espasmos na perna',
    'abnormal appearing tongue': 'língua com aparência anormal',
    'ache all over': 'dor no corpo todo',
    'lower body pain': 'dor na parte inferior do corpo',
    'problems during pregnancy': 'problemas durante gravidez',
    'spotting or bleeding during pregnancy': 'sangramento durante gravidez',
    'cramps and spasms': 'cãibras e espasmos',
    'stomach bloating': 'inchaço estomacal',
    'changes in stool appearance': 'mudanças na aparência das fezes',
    'unusual color or odor to urine': 'cor ou odor incomum na urina',
    'kidney mass': 'massa no rim',
    'swollen abdomen': 'abdômen inchado',
    'symptoms of prostate': 'sintomas na próstata',
    'leg stiffness or tightness': 'rigidez na perna',
    'rib pain': 'dor nas costelas',
    'muscle stiffness or tightness': 'rigidez muscular',
    'hand or finger lump or mass': 'massa ou caroço na mão ou dedo',
    'groin pain': 'dor na virilha',
    'abdominal distention': 'distensão abdominal',
    'regurgitation.1': 'regurgitação',
    'symptoms of the kidneys': 'sintomas nos rins',
    'melena': 'fezes escuras com sangue',
    'shoulder cramps or spasms': 'cãibras ou espasmos no ombro',
    'joint stiffness or tightness': 'rigidez articular',
    'pain or soreness of breast': 'dor ou sensibilidade na mama',
    'excessive urination at night': 'micção excessiva à noite',
    'bleeding from eye': 'sangramento no olho',
    'rectal bleeding': 'sangramento retal',
    'temper problems': 'problemas de temperamento',
    'coryza': 'coriza',
    'wrist weakness': 'fraqueza no pulso',
    'eye strain': 'fadiga ocular',
    'lymphedema': 'linfedema',
    'skin on leg or foot looks infected': 'pele da perna ou pé parece infectada',
    'congestion in chest': 'congestionamento no peito',
    'muscle swelling': 'inchaço muscular',
    'pus in urine': 'pus na urina',
    'abnormal size or shape of ear': 'tamanho ou formato anormal da orelha',
    'low back weakness': 'fraqueza lombar',
    'sleepiness': 'sonolência',
    'abnormal breathing sounds': 'sons respiratórios anormais',
    'excessive growth': 'crescimento excessivo',
    'elbow cramps or spasms': 'cãibras ou espasmos no cotovelo',
    'feeling hot and cold': 'sensação de calor e frio',
    'blood clots during menstrual periods': 'coágulos durante menstruação',
    'pulling at ears': 'puxar as orelhas',
    'gum pain': 'dor na gengiva',
    'redness in ear': 'vermelhidão na orelha',
    'fluid retention': 'retenção de líquidos',
    'flu-like syndrome': 'síndrome gripal',
    'sinus congestion': 'congestão nos seios nasais',
    'painful sinuses': 'seios nasais doloridos',
    'fears and phobias': 'medos e fobias',
    'recent pregnancy': 'gravidez recente',
    'uterine contractions': 'contrações uterinas',
    'burning chest pain': 'dor em queimação no peito',
    'back cramps or spasms': 'cãibras ou espasmos nas costas',
    'stiffness all over': 'rigidez generalizada',
    'muscle cramps, contractures, or spasms': 'cãibras, contraturas ou espasmos musculares',
    'low back cramps or spasms': 'cãibras ou espasmos lombares',
    'back mass or lump': 'massa ou caroço nas costas',
    'nosebleed': 'sangramento nasal',
    'long menstrual periods': 'períodos menstruais longos',
    'heavy menstrual flow': 'fluxo menstrual intenso',
    'unpredictable menstruation': 'menstruação imprevisível',
    'infertility': 'infertilidade',
    'frequent menstruation': 'menstruação frequente',
    'mass on eyelid': 'massa na pálpebra',
    'swollen eye': 'olho inchado',
    'eyelid lesion or rash': 'lesão ou erupção na pálpebra',
    'unwanted hair': 'pelos indesejados',
    'symptoms of bladder': 'sintomas na bexiga',
    'irregular appearing nails': 'unhas com aparência irregular',
    'hurts to breath': 'dói ao respirar',
    'nailbiting': 'roer unhas',
    'skin dryness, peeling, scaliness, or roughness': 'pele seca, descamando ou áspera',
    'skin on arm or hand looks infected': 'pele do braço ou mão parece infectada',
    'skin irritation': 'irritação na pele',
    'itchy scalp': 'couro cabeludo com coceira',
    'hip swelling': 'inchaço no quadril',
    'incontinence of stool': 'incontinência fecal',
    'foot or toe cramps or spasms': 'cãibras ou espasmos no pé ou dedo',
    'bumps on penis': 'caroços no pênis',
    'too little hair': 'pouco cabelo',
    'foot or toe lump or mass': 'massa ou caroço no pé ou dedo',
    'mass or swelling around the anus': 'massa ou inchaço ao redor do ânus',
    'low back swelling': 'inchaço lombar',
    'ankle swelling': 'inchaço no tornozelo',
    'hip lump or mass': 'massa ou caroço no quadril',
    'drainage in throat': 'drenagem na garganta',
    'dry or flaky scalp': 'couro cabeludo seco ou descamando',
    'premenstrual tension or irritability': 'tensão ou irritabilidade pré-menstrual',
    'feeling hot': 'sensação de calor',
    'feet turned in': 'pés virados para dentro',
    'foot or toe stiffness or tightness': 'rigidez no pé ou dedo',
    'pelvic pressure': 'pressão pélvica',
    'elbow swelling': 'inchaço no cotovelo',
    'elbow stiffness or tightness': 'rigidez no cotovelo',
    'early or late onset of menopause': 'menopausa precoce ou tardia',
    'mass on ear': 'massa na orelha',
    'bleeding from ear': 'sangramento na orelha',
    'hand or finger weakness': 'fraqueza na mão ou dedo',
    'low self-esteem': 'baixa autoestima',
    'throat irritation': 'irritação na garganta',
    'itching of the anus': 'coceira no ânus',
    'swollen or red tonsils': 'amígdalas inchadas ou vermelhas',
    'irregular belly button': 'umbigo irregular',
    'swollen tongue': 'língua inchada',
    'lip sore': 'ferida no lábio',
    'vulvar sore': 'ferida vulvar',
    'hip stiffness or tightness': 'rigidez no quadril',
    'mouth pain': 'dor na boca',
    'arm weakness': 'fraqueza no braço',
    'leg lump or mass': 'massa ou caroço na perna',
    'disturbance of smell or taste': 'distúrbio de olfato ou paladar',
    'discharge in stools': 'secreção nas fezes',
    'penis pain': 'dor no pênis',
    'loss of sex drive': 'perda de libido',
    'obsessions and compulsions': 'obsessões e compulsões',
    'antisocial behavior': 'comportamento antissocial',
    'neck cramps or spasms': 'cãibras ou espasmos no pescoço',
    'pupils unequal': 'pupilas desiguais',
    'poor circulation': 'má circulação',
    'thirst': 'sede',
    'sleepwalking': 'sonambulismo',
    'skin oiliness': 'oleosidade na pele',
    'sneezing': 'espirros',
    'bladder mass': 'massa na bexiga',
    'knee cramps or spasms': 'cãibras ou espasmos no joelho',
    'premature ejaculation': 'ejaculação precoce',
    'leg weakness': 'fraqueza na perna',
    'posture problems': 'problemas de postura',
    'bleeding in mouth': 'sangramento na boca',
    'tongue bleeding': 'sangramento na língua',
    'change in skin mole size or color': 'mudança no tamanho ou cor de pinta',
    'penis redness': 'vermelhidão no pênis',
    'penile discharge': 'secreção peniana',
    'shoulder lump or mass': 'massa ou caroço no ombro',
    'polyuria': 'poliúria',
    'cloudy eye': 'olho nublado',
    'hysterical behavior': 'comportamento histérico',
    'arm lump or mass': 'massa ou caroço no braço',
    'nightmares': 'pesadelos',
    'bleeding gums': 'gengivas sangrando',
    'pain in gums': 'dor nas gengivas',
    'bedwetting': 'enurese noturna',
    'diaper rash': 'assadura',
    'lump or mass of breast': 'massa ou caroço na mama',
    'vaginal bleeding after menopause': 'sangramento vaginal após menopausa',
    'infrequent menstruation': 'menstruação infrequente',
    'mass on vulva': 'massa na vulva',
    'itching of scrotum': 'coceira no escroto',
    'postpartum problems of the breast': 'problemas mamários pós-parto',
    'eyelid retracted': 'pálpebra retraída',
    'hesitancy': 'hesitação',
    'elbow lump or mass': 'massa ou caroço no cotovelo',
    'throat redness': 'vermelhidão na garganta',
    'redness in or around nose': 'vermelhidão no ou ao redor do nariz',
    'wrinkles on skin': 'rugas na pele',
    'foot or toe weakness': 'fraqueza no pé ou dedo',
    'hand or finger cramps or spasms': 'cãibras ou espasmos na mão ou dedo',
    'back stiffness or tightness': 'rigidez nas costas',
    'wrist lump or mass': 'massa ou caroço no pulso',
    'skin pain': 'dor na pele',
    'low back stiffness or tightness': 'rigidez lombar',
    'low urine output': 'pouca produção de urina',
    'skin on head or neck looks infected': 'pele da cabeça ou pescoço parece infectada',
    'stuttering or stammering': 'gagueira',
    'problems with orgasm': 'problemas com orgasmo',
    'nose deformity': 'deformidade no nariz',
    'lump over jaw': 'caroço sobre mandíbula',
    'sore in nose': 'ferida no nariz',
    'hip weakness': 'fraqueza no quadril',
    'back swelling': 'inchaço nas costas',
    'ankle stiffness or tightness': 'rigidez no tornozelo',
    'ankle weakness': 'fraqueza no tornozelo',
    'neck weakness': 'fraqueza no pescoço',
    'depressive or psychotic symptoms': 'sintomas depressivos ou psicóticos',
    'breathing fast': 'respiração acelerada',
    'throat swelling': 'inchaço na garganta',
    'diminished hearing': 'audição diminuída',
    'lump in throat': 'caroço na garganta',
    'throat feels tight': 'garganta apertada',
    'retention of urine': 'retenção urinária',
    'groin mass': 'massa na virilha',
    'suprapubic pain': 'dor suprapúbica',
    'blood in stool': 'sangue nas fezes',
    'lack of growth': 'falta de crescimento',
    'emotional symptoms': 'sintomas emocionais',
    'elbow weakness': 'fraqueza no cotovelo',
    'back weakness': 'fraqueza nas costas',
    'intermenstrual bleeding': 'sangramento entre menstruações',
    'pain in testicles': 'dor nos testículos',
    'eye deviation': 'desvio do olho',
    'symptoms of the kidneys': 'sintomas renais',
    'delusions or hallucinations': 'delírios ou alucinações',
    'tongue pain': 'dor na língua',
    'irregular appearing nails': 'unhas com aparência irregular',
}

# Tradução das categorias
TRADUCAO_CATEGORIAS = {
    'Respiratory': 'Respiratória',
    'Cardiovascular': 'Cardiovascular',
    'Gastrointestinal': 'Gastrointestinal',
    'Neurological': 'Neurológica',
    'Musculoskeletal': 'Musculoesquelética',
    'Infectious': 'Infecciosa',
    'Endocrine_Metabolic': 'Endócrina/Metabólica',
    'Renal_Urological': 'Renal/Urológica',
    'Gynecological_Obstetric': 'Ginecológica/Obstétrica',
    'Psychiatric': 'Psiquiátrica',
    'Dermatological': 'Dermatológica',
    'Ophthalmological': 'Oftalmológica',
    'ENT': 'Ouvido/Nariz/Garganta',
    'Hematological_Oncological': 'Hematológica/Oncológica',
    'Rheumatological_Immunological': 'Reumatológica/Imunológica',
    'Other': 'Outras'
}

# Tradução dos níveis de confiança
TRADUCAO_CONFIANCA = {
    'High': 'Alta',
    'Medium': 'Média',
    'Low': 'Baixa'
}

def traduzir_sintoma(sintoma_en):
    """Traduz um sintoma do inglês para português"""
    return TRADUCAO_SINTOMAS.get(sintoma_en.lower(), sintoma_en)

def traduzir_categoria(categoria_en):
    """Traduz uma categoria do inglês para português"""
    return TRADUCAO_CATEGORIAS.get(categoria_en, categoria_en)

def traduzir_confianca(confianca_en):
    """Traduz nível de confiança do inglês para português"""
    return TRADUCAO_CONFIANCA.get(confianca_en, confianca_en)

# ========== CARREGAR MODELO E METADADOS ==========
try:
    with open('disease_classifier_model.pkl', 'rb') as f:
        model = pickle.load(f)
    
    with open('label_encoder.pkl', 'rb') as f:
        encoder = pickle.load(f)
    
    with open('symptom_columns.pkl', 'rb') as f:
        symptom_columns = pickle.load(f)
    
    with open('disease_categories.json', 'r') as f:
        disease_categories = json.load(f)
    
    logger.info("✅ Modelo carregado com sucesso!")
    logger.info(f"Total de sintomas disponíveis: {len(symptom_columns)}")
    logger.info(f"Total de categorias: {len(encoder.classes_)}")
    
except Exception as e:
    logger.error(f"❌ Erro ao carregar modelo: {str(e)}")
    raise

# ========== FUNÇÃO DE PREDIÇÃO ==========
def predict_disease_category(symptoms_dict, top_k=5):
    """
    Faz predição de categoria de doença baseado em sintomas
    
    Args:
        symptoms_dict: dict com sintomas {symptom_name: 1 or 0}
        top_k: número de categorias a retornar
    
    Returns:
        dict com predições e metadados
    """
    try:
        # Criar dataframe com todos os sintomas (default = 0)
        features = pd.DataFrame(0, index=[0], columns=symptom_columns)
        
        # Preencher sintomas fornecidos
        symptoms_found = []
        symptoms_not_found = []
        
        for symptom, value in symptoms_dict.items():
            symptom_clean = symptom.lower().strip()
            if symptom_clean in symptom_columns:
                features[symptom_clean] = int(value)
                if int(value) == 1:
                    symptoms_found.append(symptom_clean)
            else:
                symptoms_not_found.append(symptom)
        
        # Fazer predição
        probas = model.predict_proba(features)[0]
        
        # Top K categorias
        top_indices = probas.argsort()[-top_k:][::-1]
        
        predictions = []
        for idx in top_indices:
            category = encoder.classes_[idx]
            probability = float(probas[idx])
            confidence = 'High' if probability > 0.5 else 'Medium' if probability > 0.2 else 'Low'
            
            predictions.append({
                'category': category,
                'category_pt': traduzir_categoria(category),
                'probability': probability,
                'percentage': f"{probability*100:.2f}%",
                'confidence': confidence,
                'confidence_pt': traduzir_confianca(confidence)
            })
        
        # Traduzir sintomas encontrados
        symptoms_found_pt = [traduzir_sintoma(s) for s in symptoms_found]
        
        return {
            'success': True,
            'predictions': predictions,
            'metadata': {
                'total_symptoms_analyzed': len(symptoms_found),
                'symptoms_found': symptoms_found,
                'symptoms_found_pt': symptoms_found_pt,
                'symptoms_not_found': symptoms_not_found,
                'timestamp': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Erro na predição: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
#=========== Rotas de Autenticacao =========
@app.route('/login')
def login_page():
    """Página de login"""
    return render_template('login.html')

@app.route('/register')
def register_page():
    """Página de cadastro"""
    return render_template('register.html')

@app.route('/api/register', methods=['POST'])
def register():
    """Registrar novo usuário"""
    try:
        import base64
        
        # Pegar dados do formulário
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        cep = request.form.get('cep')
        data_nascimento = request.form.get('dataNascimento')
        senha = request.form.get('senha')
        confirma_senha = request.form.get('confirmaSenha')
        
        # Validações
        if not all([nome, cpf, email, telefone, cep, data_nascimento, senha, confirma_senha]):
            return jsonify({'success': False, 'error': 'Todos os campos são obrigatórios'}), 400
        
        if senha != confirma_senha:
            return jsonify({'success': False, 'error': 'As senhas não coincidem'}), 400
        
        if len(senha) < 6:
            return jsonify({'success': False, 'error': 'Senha deve ter no mínimo 6 caracteres'}), 400
        
        # ✅ PROCESSAR AVATAR EM BASE64
        foto_base64 = None
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename and allowed_file(file.filename):
                # Ler bytes da imagem
                foto_bytes = file.read()
                foto_base64_raw = base64.b64encode(foto_bytes).decode('utf-8')
                
                # Detectar tipo MIME
                extensao = file.filename.rsplit('.', 1)[1].lower()
                mime_types = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'gif': 'image/gif'
                }
                mime_type = mime_types.get(extensao, 'image/jpeg')
                
                # ✅ Montar Data URL completo COM "data:"
                foto_base64 = f"data:{mime_type};base64,{foto_base64_raw}"
        
        # Salvar no banco MySQL
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Gerar código único de usuário
            cursor.execute('SELECT MAX(CAST(SUBSTRING(cod_usuario, 2) AS UNSIGNED)) FROM usuario')
            result = cursor.fetchone()
            last_id = result[0] if result[0] else 0
            novo_cod = f'U{str(last_id + 1).zfill(3)}'
            
            # ✅ INSERIR COM BASE64 (ou NULL se não houver foto)
            cursor.execute('''
                INSERT INTO usuario (cod_usuario, CPF, Nome_user, telefone, email, 
                                   sexo, data_nasc, senha, foto, cod_cargo)
                VALUES (%s, %s, %s, %s, %s, 'NB', %s, %s, %s, 'C002')
            ''', (novo_cod, cpf, nome, telefone, email, data_nascimento, 
                  hash_senha(senha), foto_base64))
            
            conn.commit()
            
            # Fazer login automático
            session['user_id'] = novo_cod
            session['user_nome'] = nome
            session['user_email'] = email
            session['cod_cargo'] = 'C002'
            
            return jsonify({
                'success': True,
                'message': 'Cadastro realizado com sucesso!',
                'redirect': '/perfil-paciente'
            }), 201
            
        except mysql.connector.IntegrityError as e:
            error_msg = str(e)
            if 'CPF' in error_msg:
                return jsonify({'success': False, 'error': 'CPF já cadastrado'}), 400
            elif 'email' in error_msg:
                return jsonify({'success': False, 'error': 'Email já cadastrado'}), 400
            else:
                return jsonify({'success': False, 'error': 'Erro ao cadastrar usuário'}), 400
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Erro no registro: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        senha = data.get('senha')
        
        # LOG 1: O que chegou na requisição
        logger.info(f"📨 Tentativa de login - Email: {email}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT u.cod_usuario, u.Nome_user, u.email, u.senha, 
                   c.cargo_nome, c.cod_cargo
            FROM usuario u
            JOIN cargo c ON u.cod_cargo = c.cod_cargo
            WHERE u.email = %s
        ''', (email,))
        
        user = cursor.fetchone()
        
        # LOG 2: Usuário encontrado?
        if user:
            logger.info(f"✅ Usuário encontrado: {user['Nome_user']} ({user['cargo_nome']})")
            logger.info(f"🔐 Senha digitada: {senha}")
            logger.info(f"🔐 Hash digitado: {hash_senha(senha)}")
            logger.info(f"🔐 Hash no banco: {user['senha']}")
            logger.info(f"🔐 Senhas batem? {user['senha'] == hash_senha(senha)}")
        else:
            logger.warning(f"❌ Usuário NÃO encontrado para email: {email}")
        
        cursor.close()
        conn.close()
        
        if user and user['senha'] == hash_senha(senha):
            session['user_id'] = user['cod_usuario']
            session['user_nome'] = user['Nome_user']
            session['user_email'] = user['email']
            session['user_cargo'] = user['cargo_nome']
            session['cod_cargo'] = user['cod_cargo']
            
            # LOG 3: Redirecionamento
            if user['cod_cargo'] == 'C001':  # Médico
                redirect_url = '/perfil-medico'
                logger.info(f"🏥 Redirecionando MÉDICO para: {redirect_url}")
            elif user['cod_cargo'] == 'C002':  # Paciente
                redirect_url = '/perfil-paciente'
                logger.info(f"🧑 Redirecionando PACIENTE para: {redirect_url}")
            elif user['cod_cargo'] == 'C003':  # Atendente/Triagem
                redirect_url = '/perfil-atendente'  # ✅ CORRETO!
                logger.info(f"📋 Redirecionando ATENDENTE para: {redirect_url}")
            elif user['cod_cargo'] == 'C005':  # DEV
                redirect_url = '/triagem'  # ✅ CORRETO!
                logger.info(f"📋 Redirecionando PARA O TESTE DA IA para: {redirect_url}")
            elif user['cod_cargo'] == 'C006':  # Atendente/Triagem
                redirect_url = '/perfil-enfermeiro'  # ✅ CORRETO!
                logger.info(f"📋 Redirecionando PARA O TESTE DA IA para: {redirect_url}")
            else:
                redirect_url = '/perfil-paciente'
                logger.info(f"❓ Redirecionando OUTRO para: {redirect_url}")
            
            return jsonify({
                'success': True,
                'message': 'Login realizado!',
                'redirect': redirect_url,
                'user_type': user['cargo_nome']
            })
        else:
            logger.warning(f"❌ Senha incorreta para: {email}")
            return jsonify({'success': False, 'error': 'Email ou senha inválidos'}), 401
            
    except Exception as e:
        logger.error(f"💥 Erro no login: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """Fazer logout"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logout realizado com sucesso!'})

# ========== ROTAS DE SOLICITAÇÃO DE CONSULTA ==========
# ========== ROTAS DO ATENDENTE ==========

@app.route('/perfil-atendente')
@login_required
def perfil_atendente():
    """Perfil do atendente com solicitações pendentes"""
    # ✅ Permitir acesso de C003 (atendente) e C005 (dev)
    if session.get('cod_cargo') not in ['C003', 'C005']:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Buscar dados do atendente
    cursor.execute('''
        SELECT u.Nome_user, u.email, u.foto
        FROM usuario u
        WHERE u.cod_usuario = %s
    ''', (session['user_id'],))
    
    atendente = cursor.fetchone()
    if atendente and atendente.get('foto'):
        atendente['foto'] = f"/static/uploads/avatars/{atendente['foto']}"
    
    # Buscar solicitações pendentes (Aguardando Triagem) - QUERY MELHORADA
    cursor.execute('''
        SELECT 
            c.cod_consulta, 
            c.data_consulta as data_preferencial, 
            TIME_FORMAT(c.horario_preferencial_paciente, '%H:%i') as horario_preferencial_paciente,
            c.sintomas_descritos, 
            u.Nome_user as paciente, 
            u.telefone,
            u.email as email_paciente,
            un.nome_unidade, 
            un.cod_unidade,
            un.endereco as endereco_unidade,
            DATE_FORMAT(c.data_consulta, '%d/%m/%Y') as data_formatada
        FROM consulta c
        JOIN usuario u ON c.cod_usuario = u.cod_usuario
        JOIN unidade un ON c.cod_unidade = un.cod_unidade
        WHERE c.status_consulta = 'Aguardando Triagem'
        ORDER BY c.data_consulta ASC, c.horario_preferencial_paciente ASC
    ''')
    solicitacoes = cursor.fetchall()
    
    # Buscar estatísticas - NOVO
    cursor.execute('''
        SELECT 
            COUNT(*) as total_pendentes,
            COUNT(CASE WHEN DATE(c.data_consulta) = CURDATE() THEN 1 END) as hoje,
            COUNT(CASE WHEN DATE(c.data_consulta) = CURDATE() + INTERVAL 1 DAY THEN 1 END) as amanha
        FROM consulta c
        WHERE c.status_consulta = 'Aguardando Triagem'
    ''')
    stats = cursor.fetchone()
    
    # Buscar enfermeiros ativos
    cursor.execute('''
        SELECT 
            e.cod_enfermeiro, 
            u.Nome_user as nome, 
            e.COREN,
            e.especialidade,
            e.anos_experiencia
        FROM enfermeiro e
        JOIN usuario u ON e.cod_usuario = u.cod_usuario
        WHERE e.atividade = TRUE
        ORDER BY u.Nome_user
    ''')
    enfermeiros = cursor.fetchall()
    
    # Buscar unidades ativas - NOVO
    cursor.execute('SELECT * FROM unidade WHERE ativo = TRUE ORDER BY nome_unidade')
    unidades = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('perfil-atendente.html', 
                         atendente=atendente,
                         solicitacoes=solicitacoes,
                         enfermeiros=enfermeiros,
                         unidades=unidades,
                         stats=stats)


@app.route('/api/salas-disponiveis', methods=['GET'])
@login_required
def get_salas_disponiveis():
    """Buscar salas disponíveis por unidade e data"""
    try:
        cod_unidade = request.args.get('cod_unidade')
        data_triagem = request.args.get('data_triagem')
        hora_triagem = request.args.get('hora_triagem')
        
        if not all([cod_unidade, data_triagem, hora_triagem]):
            return jsonify({'success': False, 'error': 'Parâmetros incompletos'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar salas de triagem da unidade que NÃO estão ocupadas naquele horário
        cursor.execute('''
            SELECT s.cod_sala, s.numero_sala, s.tipo_sala
            FROM sala s
            WHERE s.cod_unidade = %s 
            AND s.tipo_sala = 'Triagem' 
            AND s.ativo = TRUE
            AND s.cod_sala NOT IN (
                SELECT c.cod_sala 
                FROM consulta c 
                WHERE c.data_consulta = %s 
                AND c.hora_consulta = %s
                AND c.cod_sala IS NOT NULL
                AND c.status_consulta NOT IN ('Cancelada', 'Concluída')
            )
            ORDER BY s.numero_sala
        ''', (cod_unidade, data_triagem, hora_triagem))
        
        salas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'salas': salas,
            'total': len(salas)
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar salas: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/verificar-disponibilidade-enfermeiro', methods=['GET'])
@login_required
def verificar_disponibilidade_enfermeiro():
    """Verificar se enfermeiro está disponível em determinado horário"""
    try:
        cod_enfermeiro = request.args.get('cod_enfermeiro')
        data_triagem = request.args.get('data_triagem')
        hora_triagem = request.args.get('hora_triagem')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se enfermeiro já tem triagem marcada neste horário
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM consulta c
            JOIN triagem t ON c.cod_consulta = t.cod_consulta
            WHERE t.cod_enfermeiro = %s
            AND c.data_consulta = %s
            AND c.hora_consulta = %s
            AND c.status_consulta NOT IN ('Cancelada', 'Concluída')
        ''', (cod_enfermeiro, data_triagem, hora_triagem))
        
        result = cursor.fetchone()
        disponivel = result['total'] == 0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'disponivel': disponivel
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar disponibilidade: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/agendar-triagem', methods=['POST'])
@login_required
def agendar_triagem():
    """Atendente agenda a triagem com enfermeiro, sala e horário"""
    try:
        # ✅ Permitir C003 (atendente) e C005 (dev)
        if session.get('cod_cargo') not in ['C003', 'C005']:
            return jsonify({'success': False, 'error': 'Acesso restrito a atendentes'}), 403
        
        data = request.get_json()
        
        cod_consulta = data.get('cod_consulta')
        cod_enfermeiro = data.get('cod_enfermeiro')
        cod_sala = data.get('cod_sala')
        data_triagem = data.get('data_triagem')
        hora_triagem = data.get('hora_triagem')
        observacoes = data.get('observacoes', '')
        
        # Validações
        if not all([cod_consulta, cod_enfermeiro, cod_sala, data_triagem, hora_triagem]):
            return jsonify({'success': False, 'error': 'Todos os campos são obrigatórios'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se consulta existe e está aguardando triagem
        cursor.execute('''
            SELECT cod_usuario, cod_unidade
            FROM consulta 
            WHERE cod_consulta = %s 
            AND status_consulta = 'Aguardando Triagem'
        ''', (cod_consulta,))
        
        consulta_info = cursor.fetchone()
        if not consulta_info:
            return jsonify({'success': False, 'error': 'Consulta não encontrada ou já processada'}), 404
        
        cod_paciente = consulta_info['cod_usuario']
        
        # Verificar se sala está disponível
        cursor.execute('''
            SELECT COUNT(*) as ocupada
            FROM consulta
            WHERE cod_sala = %s
            AND data_consulta = %s
            AND hora_consulta = %s
            AND status_consulta NOT IN ('Cancelada', 'Concluída')
        ''', (cod_sala, data_triagem, hora_triagem))
        
        if cursor.fetchone()['ocupada'] > 0:
            return jsonify({'success': False, 'error': 'Sala já ocupada neste horário'}), 400
        
        # Verificar se enfermeiro está disponível
        cursor.execute('''
            SELECT COUNT(*) as ocupado
            FROM consulta c
            JOIN triagem t ON c.cod_consulta = t.cod_consulta
            WHERE t.cod_enfermeiro = %s
            AND c.data_consulta = %s
            AND c.hora_consulta = %s
            AND c.status_consulta NOT IN ('Cancelada', 'Concluída')
        ''', (cod_enfermeiro, data_triagem, hora_triagem))
        
        if cursor.fetchone()['ocupado'] > 0:
            return jsonify({'success': False, 'error': 'Enfermeiro já tem triagem neste horário'}), 400
        
        # ✅ CORREÇÃO AQUI: usar 'Confirmada' ao invés de 'Triagem Confirmada'
        cursor.execute('''
            UPDATE consulta 
            SET 
                data_consulta = %s, 
                hora_consulta = %s, 
                cod_sala = %s,
                status_consulta = 'Confirmada'
            WHERE cod_consulta = %s
        ''', (data_triagem, hora_triagem, cod_sala, cod_consulta))
        
        # Gerar código de triagem
        cursor.execute('SELECT MAX(CAST(SUBSTRING(cod_triagem, 2) AS UNSIGNED)) FROM triagem')
        result = cursor.fetchone()
        last_id = list(result.values())[0] if result and list(result.values())[0] else 0
        novo_cod_triagem = f'T{str(last_id + 1).zfill(3)}'
        
        # Criar registro na tabela triagem
        cursor.execute('''
            INSERT INTO triagem 
            (cod_triagem, cod_consulta, sintomas_relatados, nivel_urgencia, 
             observacoes_triagem, cod_atendente, cod_enfermeiro)
            VALUES (%s, %s, 
                (SELECT sintomas_descritos FROM consulta WHERE cod_consulta = %s), 
                'Rotina', %s, %s, %s)
        ''', (novo_cod_triagem, cod_consulta, cod_consulta, observacoes, 
              session['user_id'], cod_enfermeiro))
        
        # Buscar informações para as notificações
        cursor.execute('''
            SELECT u.Nome_user as paciente, s.numero_sala, un.nome_unidade
            FROM consulta c
            JOIN usuario u ON c.cod_usuario = u.cod_usuario
            JOIN sala s ON c.cod_sala = s.cod_sala
            JOIN unidade un ON s.cod_unidade = un.cod_unidade
            WHERE c.cod_consulta = %s
        ''', (cod_consulta,))
        
        info = cursor.fetchone()
        
        cursor.execute('''
            SELECT u.Nome_user as enfermeiro
            FROM enfermeiro e
            JOIN usuario u ON e.cod_usuario = u.cod_usuario
            WHERE e.cod_enfermeiro = %s
        ''', (cod_enfermeiro,))
        
        enfermeiro_info = cursor.fetchone()
        
        # Criar notificação para o PACIENTE
        cursor.execute('''
            INSERT INTO notificacao 
            (cod_notificacao, tipo_notificacao, titulo, mensagem, cod_usuario_destino, cod_consulta)
            SELECT 
                CONCAT('N', LPAD(COALESCE(MAX(CAST(SUBSTRING(cod_notificacao, 2) AS UNSIGNED)), 0) + 1, 3, '0')),
                'Triagem Agendada',
                'Triagem Confirmada',
                CONCAT('Sua triagem foi agendada para ', DATE_FORMAT(%s, '%%d/%%m/%%Y'), ' às ', %s, 
                       ' na sala ', %s, ' - ', %s, '. Enfermeiro(a): ', %s),
                %s,
                %s
            FROM notificacao
        ''', (data_triagem, hora_triagem, info['numero_sala'], info['nome_unidade'], 
              enfermeiro_info['enfermeiro'], cod_paciente, cod_consulta))
        
        # Criar notificação para o ENFERMEIRO
        cursor.execute('SELECT cod_usuario FROM enfermeiro WHERE cod_enfermeiro = %s', (cod_enfermeiro,))
        cod_usuario_enfermeiro = cursor.fetchone()['cod_usuario']
        
        cursor.execute('''
            INSERT INTO notificacao 
            (cod_notificacao, tipo_notificacao, titulo, mensagem, cod_usuario_destino, cod_consulta)
            SELECT 
                CONCAT('N', LPAD(COALESCE(MAX(CAST(SUBSTRING(cod_notificacao, 2) AS UNSIGNED)), 0) + 1, 3, '0')),
                'Triagem Agendada',
                'Nova Triagem Atribuída',
                CONCAT('Você foi designado para realizar triagem do(a) paciente ', %s, 
                       ' em ', DATE_FORMAT(%s, '%%d/%%m/%%Y'), ' às ', %s, 
                       ' - Sala ', %s, ' (', %s, ')'),
                %s,
                %s
            FROM notificacao
        ''', (info['paciente'], data_triagem, hora_triagem, info['numero_sala'], 
              info['nome_unidade'], cod_usuario_enfermeiro, cod_consulta))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Triagem agendada com sucesso!',
            'cod_triagem': novo_cod_triagem,
            'detalhes': {
                'paciente': info['paciente'],
                'data': data_triagem,
                'hora': hora_triagem,
                'sala': info['numero_sala'],
                'unidade': info['nome_unidade'],
                'enfermeiro': enfermeiro_info['enfermeiro']
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao agendar triagem: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/solicitacao/cancelar', methods=['POST'])
@login_required
def cancelar_solicitacao():
    """Cancelar solicitação de consulta"""
    try:
        data = request.get_json()
        cod_consulta = data.get('cod_consulta')
        motivo = data.get('motivo', 'Cancelado pela recepção')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se consulta existe
        cursor.execute('''
            SELECT cod_usuario 
            FROM consulta 
            WHERE cod_consulta = %s 
            AND status_consulta = 'Aguardando Triagem'
        ''', (cod_consulta,))
        
        consulta = cursor.fetchone()
        if not consulta:
            return jsonify({'success': False, 'error': 'Consulta não encontrada'}), 404
        
        # Atualizar status
        cursor.execute('''
            UPDATE consulta 
            SET status_consulta = 'Cancelada'
            WHERE cod_consulta = %s
        ''', (cod_consulta,))
        
        # Notificar paciente
        cursor.execute('''
            INSERT INTO notificacao 
            (cod_notificacao, tipo_notificacao, titulo, mensagem, cod_usuario_destino, cod_consulta)
            SELECT 
                CONCAT('N', LPAD(COALESCE(MAX(CAST(SUBSTRING(cod_notificacao, 2) AS UNSIGNED)), 0) + 1, 3, '0')),
                'Geral',
                'Solicitação Cancelada',
                CONCAT('Sua solicitação de consulta foi cancelada. Motivo: ', %s),
                %s,
                %s
            FROM notificacao
        ''', (motivo, consulta['cod_usuario'], cod_consulta))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Solicitação cancelada'})
        
    except Exception as e:
        logger.error(f"Erro ao cancelar solicitação: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/solicitar-consulta')
@login_required
def solicitar_consulta_page():
    """Página para solicitar consulta"""
    # ✅ Permitir acesso de C002 (paciente) e C005 (dev)
    if session.get('cod_cargo') not in ['C002', 'C005']:
        return redirect('/login')
    
    # Buscar unidades disponíveis
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM unidade WHERE ativo = TRUE')
    unidades = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('solicitar-consulta.html', unidades=unidades)

# ========== ADICIONAR NO app.py APÓS AS OUTRAS ROTAS DE CONSULTA ==========

@app.route('/api/consulta/detalhes/<cod_consulta>', methods=['GET'])
@login_required
def get_consulta_detalhes(cod_consulta):
    """Buscar TODOS os detalhes de uma consulta específica"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Query COMPLETA com TODAS as informações
        cursor.execute('''
            SELECT 
                c.cod_consulta,
                c.data_consulta,
                c.hora_consulta,
                c.tipo_atendimento,
                c.status_consulta,
                c.sintomas_descritos,
                c.horario_preferencial_paciente,
                c.local_consulta,
                
                -- Médico
                COALESCE(u_medico.Nome_user, 'Aguardando Atribuição') as medico,
                m.especialidade,
                m.CRM,
                
                -- Unidade e Sala
                un.nome_unidade as unidade,
                un.endereco as endereco_unidade,
                un.telefone as telefone_unidade,
                s.numero_sala as sala,
                s.tipo_sala,
                
                -- Convênio
                conv.nome_convenio as convenio,
                conv.tipo_convenio,
                
                -- Triagem (se existir)
                t.cod_triagem,
                t.data_triagem,
                t.nivel_urgencia,
                t.categoria_ia,
                t.probabilidade_ia,
                t.observacoes_triagem,
                u_enf.Nome_user as enfermeiro,
                e.COREN,
                
                -- Atendente (se tiver agendado triagem)
                u_atend.Nome_user as atendente
                
            FROM consulta c
            
            -- Joins do médico
            LEFT JOIN medico m ON c.cod_medico = m.cod_medico
            LEFT JOIN usuario u_medico ON m.cod_usuario = u_medico.cod_usuario
            
            -- Joins da unidade e sala
            LEFT JOIN unidade un ON c.cod_unidade = un.cod_unidade
            LEFT JOIN sala s ON c.cod_sala = s.cod_sala
            
            -- Join do convênio
            LEFT JOIN convenio conv ON c.cod_convenio = conv.cod_convenio
            
            -- Joins da triagem
            LEFT JOIN triagem t ON c.cod_consulta = t.cod_consulta
            LEFT JOIN enfermeiro e ON t.cod_enfermeiro = e.cod_enfermeiro
            LEFT JOIN usuario u_enf ON e.cod_usuario = u_enf.cod_usuario
            LEFT JOIN usuario u_atend ON t.cod_atendente = u_atend.cod_usuario
            
            WHERE c.cod_consulta = %s
            AND c.cod_usuario = %s
        ''', (cod_consulta, session['user_id']))
        
        consulta = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not consulta:
            return jsonify({
                'success': False,
                'error': 'Consulta não encontrada ou você não tem permissão para visualizá-la'
            }), 404
        
        # Formatar datas
        if consulta['data_consulta']:
            consulta['data_consulta'] = consulta['data_consulta'].strftime('%d/%m/%Y')
        
        if consulta['data_triagem']:
            consulta['data_triagem'] = consulta['data_triagem'].strftime('%d/%m/%Y às %H:%M')
        
        if consulta['hora_consulta']:
            # Converter timedelta para string formatada
            hora = str(consulta['hora_consulta'])
            if len(hora.split(':')) == 3:
                h, m, s = hora.split(':')
                consulta['hora_consulta'] = f"{h}:{m}"
            else:
                consulta['hora_consulta'] = hora
        
        if consulta['horario_preferencial_paciente']:
            hora_pref = str(consulta['horario_preferencial_paciente'])
            if len(hora_pref.split(':')) == 3:
                h, m, s = hora_pref.split(':')
                consulta['horario_preferencial_paciente'] = f"{h}:{m}"
            else:
                consulta['horario_preferencial_paciente'] = hora_pref
        
        # Organizar dados da triagem se existir
        triagem_info = None
        if consulta['cod_triagem']:
            triagem_info = {
                'cod_triagem': consulta['cod_triagem'],
                'data_triagem': consulta['data_triagem'],
                'nivel_urgencia': consulta['nivel_urgencia'],
                'categoria_ia': consulta['categoria_ia'],
                'probabilidade_ia': float(consulta['probabilidade_ia']) if consulta['probabilidade_ia'] else None,
                'observacoes': consulta['observacoes_triagem'],
                'enfermeiro': consulta['enfermeiro'],
                'coren': consulta['COREN']
            }
        
        # Montar resposta final
        response_data = {
            'cod_consulta': consulta['cod_consulta'],
            'data_consulta': consulta['data_consulta'],
            'hora_consulta': consulta['hora_consulta'],
            'horario_preferencial': consulta['horario_preferencial_paciente'],
            'tipo_atendimento': consulta['tipo_atendimento'],
            'status_consulta': consulta['status_consulta'],
            'sintomas_descritos': consulta['sintomas_descritos'],
            'local_consulta': consulta['local_consulta'],
            
            # Profissional
            'medico': consulta['medico'],
            'especialidade': consulta['especialidade'],
            'crm': consulta['CRM'],
            
            # Localização
            'unidade': consulta['unidade'],
            'endereco_unidade': consulta['endereco_unidade'],
            'telefone_unidade': consulta['telefone_unidade'],
            'sala': consulta['sala'],
            'tipo_sala': consulta['tipo_sala'],
            
            # Convênio
            'convenio': consulta['convenio'],
            'tipo_convenio': str(consulta['tipo_convenio']) if consulta['tipo_convenio'] else None,
            
            # Triagem
            'triagem': triagem_info,
            
            # Atendente
            'atendente': consulta['atendente']
        }
        
        return jsonify({
            'success': True,
            'consulta': response_data
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes da consulta: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== API DE SOLICITAR CONSULTA (POST) ==========
# ========== API DE SOLICITAR CONSULTA (POST) ==========
@app.route('/api/solicitar-consulta', methods=['POST'])
@login_required
def solicitar_consulta():
    """Paciente solicita consulta (SEM escolher médico)"""
    try:
        data = request.get_json()
        
        sintomas_descritos = data.get('sintomas_descritos')
        data_preferencial = data.get('data_preferencial')
        hora_preferencial = data.get('hora_preferencial')
        cod_unidade = data.get('cod_unidade')
        
        if not all([sintomas_descritos, data_preferencial, hora_preferencial, cod_unidade]):
            return jsonify({'success': False, 'error': 'Preencha todos os campos obrigatórios'}), 400
        
        if len(sintomas_descritos) < 50:
            return jsonify({'success': False, 'error': 'Descreva seus sintomas com mais detalhes (mínimo 50 caracteres)'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Gerar código
        cursor.execute('SELECT MAX(CAST(SUBSTRING(cod_consulta, 2) AS UNSIGNED)) FROM consulta')
        result = cursor.fetchone()
        last_id = list(result.values())[0] if result and list(result.values())[0] else 0
        novo_cod = f'C{str(last_id + 1).zfill(3)}'
        
        # Buscar convênio padrão
        cursor.execute('SELECT cod_convenio FROM convenio LIMIT 1')
        convenio = cursor.fetchone()
        cod_convenio = convenio['cod_convenio'] if convenio else 'CV001'
        
        # ✅ CORRIGIDO: Inserir SEM médico, SEM sala, SEM hora definida
        cursor.execute('''
            INSERT INTO consulta 
            (cod_consulta, data_consulta, hora_consulta, horario_preferencial_paciente,
             tipo_atendimento, status_consulta, cod_medico, cod_usuario, cod_convenio, 
             cod_unidade, sintomas_descritos, cod_sala)
            VALUES (%s, %s, NULL, %s, 'Rotina', 'Aguardando Triagem', NULL, %s, %s, %s, %s, NULL)
        ''', (novo_cod, data_preferencial, hora_preferencial, session['user_id'], 
              cod_convenio, cod_unidade, sintomas_descritos))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Solicitação enviada! Aguarde o agendamento da triagem.',
            'cod_consulta': novo_cod
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao solicitar consulta: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/unidades', methods=['GET'])
def get_unidades():
    """Retornar unidades ativas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT * FROM unidade WHERE ativo = TRUE')
        unidades = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'unidades': unidades})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/medicos-por-especialidade', methods=['GET'])
@login_required
def medicos_por_especialidade():
    """Retornar médicos de uma especialidade específica"""
    try:
        especialidade = request.args.get('especialidade')
        
        if not especialidade:
            return jsonify({'success': False, 'error': 'Especialidade não informada'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT m.cod_medico, u.Nome_user as nome, m.CRM as crm, 
                   m.especialidade, m.anos_experiencia
            FROM medico m
            JOIN usuario u ON m.cod_usuario = u.cod_usuario
            WHERE m.especialidade = %s AND m.atividade = TRUE
            ORDER BY u.Nome_user
        ''', (especialidade,))
        
        medicos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'medicos': medicos,
            'total': len(medicos)
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar médicos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/medico-info', methods=['GET'])
@login_required
def medico_info():
    """Retornar informações de um médico específico"""
    try:
        cod_medico = request.args.get('cod_medico')
        
        if not cod_medico:
            return jsonify({'success': False, 'error': 'Código do médico não informado'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT u.Nome_user as nome, m.CRM as crm, 
                   m.especialidade, m.anos_experiencia
            FROM medico m
            JOIN usuario u ON m.cod_usuario = u.cod_usuario
            WHERE m.cod_medico = %s
        ''', (cod_medico,))
        
        medico = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if medico:
            return jsonify({
                'success': True,
                'medico': medico
            })
        else:
            return jsonify({'success': False, 'error': 'Médico não encontrado'}), 404
        
    except Exception as e:
        logger.error(f"Erro ao buscar informações do médico: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/perfil-medico')
@login_required
def perfil_medico():
    # ✅ Permitir acesso de C001 (médico) e C005 (dev)
    if session.get('cod_cargo') not in ['C001', 'C005']:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Buscar dados do médico COM A FOTO
    cursor.execute('''
        SELECT u.Nome_user, u.email, u.telefone, u.foto,
               m.CRM, m.especialidade, m.anos_experiencia, m.atividade
        FROM usuario u
        JOIN medico m ON u.cod_usuario = m.cod_usuario
        WHERE u.cod_usuario = %s
    ''', (session['user_id'],))
    
    medico = cursor.fetchone()
    
    # Log para debug
    logger.info(f"Foto do médico no banco: {medico.get('foto')}")
    
    # Se tem foto, ajustar o caminho
    if medico and medico.get('foto'):
        if medico['foto'].startswith('data:'):
            # Já está em base64, não mexer
            pass
        elif '.' in medico['foto']:
            # Formato antigo (nome de arquivo)
            medico['foto'] = f"/static/uploads/avatars/{medico['foto']}"
        else:
            # Base64 puro, adicionar prefixo
            medico['foto'] = f"data:image/jpeg;base64,{medico['foto']}"
    else:
        medico['foto'] = '/static/images/default-avatar-image.jpg'
    
    # Buscar consultas do dia (USAR %s)
    cursor.execute('''
        SELECT c.hora_consulta, u2.Nome_user as paciente, 
               c.tipo_atendimento, c.cod_consulta
        FROM consulta c
        JOIN usuario u2 ON c.cod_usuario = u2.cod_usuario
        WHERE c.cod_medico = (SELECT cod_medico FROM medico WHERE cod_usuario = %s)
        AND c.data_consulta = CURDATE()
        ORDER BY c.hora_consulta
    ''', (session['user_id'],))
    
    consultas = cursor.fetchall()
    
    # Calcular estatísticas (USAR %s)
    cursor.execute('''
        SELECT 
            COUNT(*) as total_consultas,
            SUM(CASE WHEN tipo_atendimento = 'Retorno' THEN 1 ELSE 0 END) as retornos
        FROM consulta
        WHERE cod_medico = (SELECT cod_medico FROM medico WHERE cod_usuario = %s)
        AND data_consulta = CURDATE()
    ''', (session['user_id'],))
    
    stats = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('perfil-medico.html', 
                         medico=medico, 
                         consultas=consultas, 
                         stats=stats)


# ========== ROTAS DO ENFERMEIRO ==========

@app.route('/perfil-enfermeiro')
@login_required
def perfil_enfermeiro():
    """Perfil do enfermeiro com triagens agendadas"""
    # ✅ Permitir acesso de C006 (enfermeiro) e C005 (dev)
    if session.get('cod_cargo') not in ['C006', 'C005']:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Buscar dados do enfermeiro COM FOTO
    cursor.execute('''
        SELECT u.Nome_user, u.email, u.telefone, u.foto,
               e.COREN, e.especialidade, e.anos_experiencia
        FROM usuario u
        JOIN enfermeiro e ON u.cod_usuario = e.cod_usuario
        WHERE u.cod_usuario = %s
    ''', (session['user_id'],))
    
    enfermeiro = cursor.fetchone()
    
    # ✅ CORREÇÃO: Ajustar foto (igual ao perfil-paciente e perfil-medico)
    if enfermeiro and enfermeiro.get('foto'):
        if enfermeiro['foto'].startswith('data:'):
            # Já está em base64 completo
            pass
        elif '.' in enfermeiro['foto']:
            # Formato antigo (nome de arquivo)
            enfermeiro['foto'] = f"/static/uploads/avatars/{enfermeiro['foto']}"
        else:
            # Base64 puro, adicionar prefixo
            enfermeiro['foto'] = f"data:image/jpeg;base64,{enfermeiro['foto']}"
    else:
        enfermeiro['foto'] = '/static/images/default-avatar-image.jpg'
    
    # Buscar cod_enfermeiro
    cursor.execute('''
        SELECT cod_enfermeiro FROM enfermeiro WHERE cod_usuario = %s
    ''', (session['user_id'],))
    
    enf_data = cursor.fetchone()
    cod_enfermeiro = enf_data['cod_enfermeiro'] if enf_data else None
    
    # ✅ CORREÇÃO: Buscar triagens COM FORMATAÇÃO CORRETA DE DATA/HORA
    cursor.execute('''
    SELECT 
        c.cod_consulta,
        c.data_consulta,
        c.hora_consulta,
        c.sintomas_descritos,
        u.Nome_user as paciente,
        u.CPF,
        u.telefone,
        un.nome_unidade,
        s.numero_sala,
        COALESCE(t.nivel_urgencia, 'Rotina') as nivel_urgencia
        FROM consulta c
        JOIN triagem t ON c.cod_consulta = t.cod_consulta
        JOIN usuario u ON c.cod_usuario = u.cod_usuario
        JOIN unidade un ON c.cod_unidade = un.cod_unidade
        JOIN sala s ON c.cod_sala = s.cod_sala
        WHERE t.cod_enfermeiro = %s
        AND c.status_consulta = 'Confirmada'
        AND c.data_consulta >= CURDATE()
        ORDER BY c.data_consulta ASC, c.hora_consulta ASC
    ''', (cod_enfermeiro,))

    triagens = cursor.fetchall()
    logger.info(f"📋 Total de triagens encontradas: {len(triagens)}")
    if triagens:
        logger.info(f"📋 Primeira triagem: {triagens[0]}")
    # ✅ FORMATAR DATAS AQUI NO PYTHON
    for triagem in triagens:
        if triagem.get('data_consulta'):
            triagem['data_formatada'] = triagem['data_consulta'].strftime('%d/%m/%Y')
        if triagem.get('hora_consulta'):
            hora = str(triagem['hora_consulta'])
            if len(hora.split(':')) >= 2:
                h, m = hora.split(':')[:2]
                triagem['hora_consulta'] = f"{h}:{m}"
    
    # Estatísticas
    cursor.execute('''
        SELECT 
            COUNT(*) as total_agendadas,
            COUNT(CASE WHEN DATE(c.data_consulta) = CURDATE() THEN 1 END) as hoje
        FROM consulta c
        JOIN triagem t ON c.cod_consulta = t.cod_consulta
        WHERE t.cod_enfermeiro = %s
        AND c.status_consulta = 'Confirmada'
    ''', (cod_enfermeiro,))
    
    stats_agendadas = cursor.fetchone()
    
    cursor.execute('''
        SELECT COUNT(*) as total_realizadas
        FROM consulta c
        JOIN triagem t ON c.cod_consulta = t.cod_consulta
        WHERE t.cod_enfermeiro = %s
        AND c.status_consulta = 'Aguardando Consulta'
        AND DATE(t.data_triagem) = CURDATE()
    ''', (cod_enfermeiro,))
    
    stats_realizadas = cursor.fetchone()
    
    cursor.execute('''
        SELECT COUNT(DISTINCT c.cod_usuario) as total_pacientes
        FROM consulta c
        JOIN triagem t ON c.cod_consulta = t.cod_consulta
        WHERE t.cod_enfermeiro = %s
        AND MONTH(t.data_triagem) = MONTH(CURDATE())
    ''', (cod_enfermeiro,))
    
    stats_pacientes = cursor.fetchone()
    
    stats = {
        'totalAgendadas': stats_agendadas['total_agendadas'] if stats_agendadas else 0,
        'hoje': stats_agendadas['hoje'] if stats_agendadas else 0,
        'totalRealizadas': stats_realizadas['total_realizadas'] if stats_realizadas else 0,
        'totalPacientes': stats_pacientes['total_pacientes'] if stats_pacientes else 0
    }
    
    cursor.close()
    conn.close()
    
    return render_template('perfil-enfermeiro.html',
                         enfermeiro=enfermeiro,
                         triagens=triagens,
                         stats=stats)


@app.route('/api/consulta/cancelar', methods=['POST'])
@login_required
def cancelar_consulta():
    try:
        data = request.get_json()
        cod_consulta = data.get('cod_consulta')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se a consulta pertence ao usuário logado
        cursor.execute('''
            SELECT cod_usuario, data_consulta, status_consulta 
            FROM consulta 
            WHERE cod_consulta = %s
        ''', (cod_consulta,))
        
        consulta = cursor.fetchone()
        
        if not consulta:
            return jsonify({'success': False, 'error': 'Consulta não encontrada'}), 404
        
        if consulta[0] != session['user_id']:
            return jsonify({'success': False, 'error': 'Você não tem permissão para cancelar esta consulta'}), 403
        
        # Verificar se a data da consulta já passou
        if consulta[1] < datetime.now().date():
            return jsonify({'success': False, 'error': 'Não é possível cancelar consultas passadas'}), 400
        
        # Verificar se já está cancelada
        if consulta[2] == 'Cancelada':
            return jsonify({'success': False, 'error': 'Consulta já está cancelada'}), 400
        
        # Cancelar a consulta
        cursor.execute('''
            UPDATE consulta 
            SET status_consulta = 'Cancelada'
            WHERE cod_consulta = %s
        ''', (cod_consulta,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Consulta cancelada com sucesso!'})
        
    except Exception as e:
        logger.error(f"Erro ao cancelar consulta: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/salas-por-unidade', methods=['GET'])
def get_salas_por_unidade():
    """Retornar salas de triagem de uma unidade"""
    try:
        cod_unidade = request.args.get('cod_unidade')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT cod_sala, numero_sala, tipo_sala 
            FROM sala 
            WHERE cod_unidade = %s AND tipo_sala = 'Triagem' AND ativo = TRUE
            ORDER BY numero_sala
        ''', (cod_unidade,))
        
        salas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'salas': salas})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
# ========== ROTAS DA API ==========
@app.route('/perfil-paciente')
@login_required
def perfil_paciente():
    # ✅ Permitir acesso de C002 (paciente) e C005 (dev)
    if session.get('cod_cargo') not in ['C002', 'C005']:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Buscar dados do paciente COM A FOTO
    cursor.execute('''
        SELECT u.Nome_user, u.CPF, u.email, u.telefone, u.data_nasc, u.foto
        FROM usuario u
        WHERE u.cod_usuario = %s
    ''', (session['user_id'],))
    
    paciente = cursor.fetchone()
    
    # Se tem foto, ajustar o caminho
    if paciente and paciente.get('foto'):
        if paciente['foto'].startswith('data:'):
            # Já está em base64, não mexer
            pass
        elif '.' in paciente['foto']:
            # Formato antigo (nome de arquivo)
            paciente['foto'] = f"/static/uploads/avatars/{paciente['foto']}"
        else:
            # Base64 puro, adicionar prefixo
            paciente['foto'] = f"data:image/jpeg;base64,{paciente['foto']}"
    else:
        paciente['foto'] = '/static/images/default-avatar-image.jpg'
    
    # Buscar consultas do paciente (últimas 10) - MELHORADA
    cursor.execute('''
        SELECT c.cod_consulta, c.data_consulta, c.hora_consulta, 
               c.tipo_atendimento, c.status_consulta,
               COALESCE(u2.Nome_user, 'Aguardando Atribuição') as medico,
               m.especialidade
        FROM consulta c
        LEFT JOIN medico m ON c.cod_medico = m.cod_medico
        LEFT JOIN usuario u2 ON m.cod_usuario = u2.cod_usuario
        WHERE c.cod_usuario = %s
        ORDER BY c.data_consulta DESC, c.hora_consulta DESC
        LIMIT 10
    ''', (session['user_id'],))
    
    consultas = cursor.fetchall()
    
    # Estatísticas rápidas
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status_consulta IN ('Aguardando Triagem', 'Aguardando Consulta') THEN 1 ELSE 0 END) as aguardando,
            SUM(CASE WHEN status_consulta = 'Confirmada' THEN 1 ELSE 0 END) as confirmadas,
            SUM(CASE WHEN status_consulta = 'Concluída' THEN 1 ELSE 0 END) as concluidas
        FROM consulta
        WHERE cod_usuario = %s
    ''', (session['user_id'],))
    
    stats = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('perfil-paciente.html', 
                         paciente=paciente, 
                         consultas=consultas,
                         stats=stats)



@app.route('/index')
def index_page():
    """Página inicial com verificação de login"""
    user_data = None
    if 'user_id' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT u.Nome_user, u.foto, c.cargo_nome, c.cod_cargo
            FROM usuario u
            JOIN cargo c ON u.cod_cargo = c.cod_cargo
            WHERE u.cod_usuario = %s
        ''', (session['user_id'],))
        
        user_data = cursor.fetchone()
        
        # Ajustar foto
        if user_data and user_data.get('foto'):
            if not user_data['foto'].startswith('data:'):
                if '.' in user_data['foto']:
                    user_data['foto'] = f"/static/uploads/avatars/{user_data['foto']}"
                else:
                    user_data['foto'] = f"data:image/jpeg;base64,{user_data['foto']}"
        elif user_data:
            user_data['foto'] = '/static/images/default-avatar-image.jpg'
        
        cursor.close()
        conn.close()
    
    return render_template('index.html', user=user_data)

@app.route('/')
def index():
    return redirect(url_for('index_page'))  # Mudar de 'login_page' para 'index_page'

@app.route('/admin')
@login_required
def admin_dashboard():
    """Dashboard administrativo"""
    # ✅ Permitir acesso de C004 (admin) e C005 (dev)
    if session.get('cod_cargo') not in ['C004', 'C005']:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Buscar dados do admin
    cursor.execute('''
        SELECT u.Nome_user, u.email, u.foto
        FROM usuario u
        WHERE u.cod_usuario = %s
    ''', (session['user_id'],))
    
    admin = cursor.fetchone()
    
    # Ajustar foto
    if admin and admin.get('foto'):
        if admin['foto'].startswith('data:'):
            pass
        elif '.' in admin['foto']:
            admin['foto'] = f"/static/uploads/avatars/{admin['foto']}"
        else:
            admin['foto'] = f"data:image/jpeg;base64,{admin['foto']}"
    else:
        admin['foto'] = '/static/images/default-avatar-image.jpg'
    
    # Estatísticas gerais
    cursor.execute('SELECT COUNT(*) as total FROM consulta WHERE DATE(data_consulta) = CURDATE()')
    consultas_hoje = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as total FROM usuario WHERE cod_cargo = "C002"')
    pacientes_ativos = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as total FROM medico WHERE atividade = TRUE')
    medicos_disponiveis = cursor.fetchone()['total']
    
    # Próximas consultas
    cursor.execute('''
        SELECT 
            u.Nome_user as paciente,
            COALESCE(um.Nome_user, 'Não atribuído') as medico,
            DATE_FORMAT(c.data_consulta, '%d/%m/%Y') as data,
            TIME_FORMAT(c.hora_consulta, '%H:%i') as hora,
            m.especialidade,
            c.status_consulta,
            c.cod_consulta
        FROM consulta c
        JOIN usuario u ON c.cod_usuario = u.cod_usuario
        LEFT JOIN medico m ON c.cod_medico = m.cod_medico
        LEFT JOIN usuario um ON m.cod_usuario = um.cod_usuario
        ORDER BY c.data_consulta DESC, c.hora_consulta DESC
        LIMIT 50
    ''')
    proximas_consultas = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin.html',
                         admin=admin,
                         consultas_hoje=consultas_hoje,
                         pacientes_ativos=pacientes_ativos,
                         medicos_disponiveis=medicos_disponiveis,
                         proximas_consultas=proximas_consultas)

@app.route('/api/admin/consulta/<cod_consulta>', methods=['GET'])
@login_required
def get_consulta_admin(cod_consulta):
    """Buscar detalhes de uma consulta para o admin"""
    try:
        if session.get('cod_cargo') not in ['C004', 'C005']:
            return jsonify({'success': False, 'error': 'Acesso restrito'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # ✅ QUERY COMPLETA E CORRIGIDA
        cursor.execute('''
            SELECT 
                c.cod_consulta,
                c.data_consulta,
                c.hora_consulta,
                c.horario_preferencial_paciente,
                c.status_consulta,
                c.tipo_atendimento,
                c.sintomas_descritos,
                c.local_consulta,
                
                -- Paciente
                u.Nome_user as paciente,
                u.CPF as cpf_paciente,
                u.telefone as telefone_paciente,
                
                -- Médico
                COALESCE(um.Nome_user, 'Aguardando Atribuição') as medico,
                m.especialidade,
                m.CRM,
                
                -- Unidade e Sala
                un.nome_unidade as unidade,
                un.endereco as endereco_unidade,
                un.telefone as telefone_unidade,
                s.numero_sala as sala,
                s.tipo_sala,
                
                -- Convênio
                conv.nome_convenio as convenio,
                conv.tipo_convenio,
                
                -- Triagem
                t.cod_triagem,
                t.data_triagem,
                t.nivel_urgencia,
                t.categoria_ia,
                t.probabilidade_ia,
                t.observacoes_triagem,
                t.sintomas_relatados,
                
                -- Enfermeiro
                ue.Nome_user as enfermeiro,
                e.COREN,
                
                -- Atendente
                ua.Nome_user as atendente
                
            FROM consulta c
            
            -- Paciente
            JOIN usuario u ON c.cod_usuario = u.cod_usuario
            
            -- Médico
            LEFT JOIN medico m ON c.cod_medico = m.cod_medico
            LEFT JOIN usuario um ON m.cod_usuario = um.cod_usuario
            
            -- Sala e Unidade
            LEFT JOIN sala s ON c.cod_sala = s.cod_sala
            LEFT JOIN unidade un ON s.cod_unidade = un.cod_unidade
            
            -- Convênio
            LEFT JOIN convenio conv ON c.cod_convenio = conv.cod_convenio
            
            -- Triagem
            LEFT JOIN triagem t ON c.cod_consulta = t.cod_consulta
            LEFT JOIN enfermeiro e ON t.cod_enfermeiro = e.cod_enfermeiro
            LEFT JOIN usuario ue ON e.cod_usuario = ue.cod_usuario
            LEFT JOIN usuario ua ON t.cod_atendente = ua.cod_usuario
            
            WHERE c.cod_consulta = %s
        ''', (cod_consulta,))
        
        consulta = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not consulta:
            return jsonify({'success': False, 'error': 'Consulta não encontrada'}), 404
        
        # ✅ FORMATAR DADOS COMPLETOS
        response_data = {
            'cod_consulta': consulta['cod_consulta'],
            'data_consulta': consulta['data_consulta'].strftime('%d/%m/%Y') if consulta['data_consulta'] else '-',
            'hora_consulta': str(consulta['hora_consulta']).split(':')[0] + ':' + str(consulta['hora_consulta']).split(':')[1] if consulta['hora_consulta'] else 'A definir',
            'horario_preferencial': str(consulta['horario_preferencial_paciente']).split(':')[0] + ':' + str(consulta['horario_preferencial_paciente']).split(':')[1] if consulta['horario_preferencial_paciente'] else None,
            'status_consulta': consulta['status_consulta'],
            'tipo_atendimento': consulta['tipo_atendimento'],
            'sintomas_descritos': consulta['sintomas_descritos'] or consulta['sintomas_relatados'] or 'Não informado',
            'local_consulta': consulta['local_consulta'],
            
            # Paciente
            'paciente': consulta['paciente'],
            'cpf_paciente': consulta['cpf_paciente'],
            'telefone_paciente': consulta['telefone_paciente'],
            
            # Médico
            'medico': consulta['medico'],
            'especialidade': consulta['especialidade'],
            'crm': consulta['CRM'],
            
            # Localização
            'unidade': consulta['unidade'],
            'endereco_unidade': consulta['endereco_unidade'],
            'telefone_unidade': consulta['telefone_unidade'],
            'sala': consulta['sala'],
            'tipo_sala': consulta['tipo_sala'],
            
            # Convênio
            'convenio': consulta['convenio'],
            'tipo_convenio': str(consulta['tipo_convenio']) if consulta['tipo_convenio'] else None,
            
            # Triagem
            'triagem': {
                'cod_triagem': consulta['cod_triagem'],
                'data_triagem': consulta['data_triagem'].strftime('%d/%m/%Y às %H:%M') if consulta['data_triagem'] else None,
                'nivel_urgencia': consulta['nivel_urgencia'],
                'categoria_ia': consulta['categoria_ia'],
                'probabilidade_ia': float(consulta['probabilidade_ia'] * 100) if consulta['probabilidade_ia'] else None,
                'observacoes': consulta['observacoes_triagem'],
                'enfermeiro': consulta['enfermeiro'],
                'coren': consulta['COREN'],
                'atendente': consulta['atendente']
            } if consulta['cod_triagem'] else None
        }
        
        return jsonify({'success': True, 'consulta': response_data})
        
    except Exception as e:
        logger.error(f"Erro ao buscar consulta: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/admin/usuarios', methods=['GET'])
@login_required
def listar_usuarios():
    """Listar todos os usuários (filtrado por cargo se fornecido)"""
    try:
        if session.get('cod_cargo') not in ['C004', 'C005']:
            return jsonify({'success': False, 'error': 'Acesso restrito'}), 403
        
        cargo = request.args.get('cargo', '')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Query base
        query = '''
            SELECT 
                u.cod_usuario,
                u.Nome_user,
                u.email,
                u.CPF,
                u.telefone,
                c.cargo_nome,
                u.cod_cargo,
                
                -- Dados específicos de médico
                m.CRM as registro_profissional,
                m.especialidade,
                m.anos_experiencia,
                m.atividade as ativo,
                
                -- Dados específicos de enfermeiro
                e.COREN as registro_profissional_enf,
                e.especialidade as especialidade_enf,
                e.anos_experiencia as anos_experiencia_enf,
                e.atividade as ativo_enf
                
            FROM usuario u
            JOIN cargo c ON u.cod_cargo = c.cod_cargo
            LEFT JOIN medico m ON u.cod_usuario = m.cod_usuario
            LEFT JOIN enfermeiro e ON u.cod_usuario = e.cod_usuario
        '''
        
        # Adicionar filtro se cargo foi fornecido
        if cargo:
            query += ' WHERE u.cod_cargo = %s'
            cursor.execute(query, (cargo,))
        else:
            cursor.execute(query)
        
        usuarios_raw = cursor.fetchall()
        
        # Processar resultados
        usuarios = []
        for user in usuarios_raw:
            # Determinar registro profissional e especialidade
            registro = '-'
            especialidade = '-'
            ativo = True
            
            if user['cod_cargo'] == 'C001':  # Médico
                registro = user['registro_profissional'] or '-'
                especialidade = user['especialidade'] or '-'
                ativo = user['ativo'] if user['ativo'] is not None else True
            elif user['cod_cargo'] == 'C006':  # Enfermeiro
                registro = user['registro_profissional_enf'] or '-'
                especialidade = user['especialidade_enf'] or '-'
                ativo = user['ativo_enf'] if user['ativo_enf'] is not None else True
            
            usuarios.append({
                'cod_usuario': user['cod_usuario'],
                'Nome_user': user['Nome_user'],
                'email': user['email'],
                'CPF': user['CPF'],
                'telefone': user['telefone'],
                'cargo_nome': user['cargo_nome'],
                'cod_cargo': user['cod_cargo'],
                'registro_profissional': registro,
                'especialidade': especialidade,
                'ativo': ativo
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'usuarios': usuarios
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
        
@app.route('/api/admin/cadastrar-usuario', methods=['POST'])
@login_required
def cadastrar_usuario_admin():
    """Admin cadastra novo usuário (médico, enfermeiro, atendente, etc)"""
    try:
        if session.get('cod_cargo') not in ['C004', 'C005']:
            return jsonify({'success': False, 'error': 'Acesso restrito'}), 403
        
        data = request.get_json()
        
        nome = data.get('nome')
        cpf = data.get('cpf')
        email = data.get('email')
        telefone = data.get('telefone')
        data_nasc = data.get('data_nasc')
        sexo = data.get('sexo', 'NB')
        cod_cargo = data.get('cod_cargo')
        senha = gerar_senha_forte(12)  # Gera senha forte aleatória de 12 caracteres
        
        # Dados específicos por cargo
        crm = data.get('crm')  # Para médicos
        especialidade = data.get('especialidade')
        anos_experiencia = data.get('anos_experiencia', 0)
        coren = data.get('coren')  # Para enfermeiros
        
        # Validações
        if not all([nome, cpf, email, telefone, data_nasc, cod_cargo]):
            return jsonify({'success': False, 'error': 'Preencha todos os campos obrigatórios'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Gerar código de usuário
        cursor.execute('SELECT MAX(CAST(SUBSTRING(cod_usuario, 2) AS UNSIGNED)) FROM usuario')
        result = cursor.fetchone()
        last_id = list(result.values())[0] if result and list(result.values())[0] else 0
        novo_cod = f'U{str(last_id + 1).zfill(3)}'
        
        # Inserir usuário
        cursor.execute('''
            INSERT INTO usuario (cod_usuario, CPF, Nome_user, telefone, email, sexo, data_nasc, senha, cod_cargo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (novo_cod, cpf, nome, telefone, email, sexo, data_nasc, hash_senha(senha), cod_cargo))
        
        # Se for médico, inserir na tabela medico
        if cod_cargo == 'C001':
            if not crm or not especialidade:
                return jsonify({'success': False, 'error': 'CRM e especialidade são obrigatórios para médicos'}), 400
            
            cursor.execute('SELECT MAX(CAST(SUBSTRING(cod_medico, 2) AS UNSIGNED)) FROM medico')
            result = cursor.fetchone()
            last_id_med = list(result.values())[0] if result and list(result.values())[0] else 0
            cod_medico = f'M{str(last_id_med + 1).zfill(3)}'
            
            cursor.execute('''
                INSERT INTO medico (cod_medico, CRM, especialidade, anos_experiencia, atividade, cod_usuario)
                VALUES (%s, %s, %s, %s, TRUE, %s)
            ''', (cod_medico, crm, especialidade, anos_experiencia, novo_cod))
        
        # Se for enfermeiro, inserir na tabela enfermeiro
        elif cod_cargo == 'C006':
            if not coren:
                return jsonify({'success': False, 'error': 'COREN é obrigatório para enfermeiros'}), 400
            
            cursor.execute('SELECT MAX(CAST(SUBSTRING(cod_enfermeiro, 2) AS UNSIGNED)) FROM enfermeiro')
            result = cursor.fetchone()
            last_id_enf = list(result.values())[0] if result and list(result.values())[0] else 0
            cod_enfermeiro = f'E{str(last_id_enf + 1).zfill(3)}'
            
            cursor.execute('''
                INSERT INTO enfermeiro (cod_enfermeiro, COREN, especialidade, anos_experiencia, atividade, cod_usuario)
                VALUES (%s, %s, %s, %s, TRUE, %s)
            ''', (cod_enfermeiro, coren, especialidade or 'Triagem', anos_experiencia, novo_cod))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Usuário {nome} cadastrado com sucesso!',
            'cod_usuario': novo_cod,
            'senha_gerada': senha  # ✅ Retornar a senha para exibir ao admin
        }), 201
        
    except mysql.connector.IntegrityError as e:
        if 'CPF' in str(e):
            return jsonify({'success': False, 'error': 'CPF já cadastrado'}), 400
        elif 'email' in str(e):
            return jsonify({'success': False, 'error': 'Email já cadastrado'}), 400
        elif 'CRM' in str(e):
            return jsonify({'success': False, 'error': 'CRM já cadastrado'}), 400
        elif 'COREN' in str(e):
            return jsonify({'success': False, 'error': 'COREN já cadastrado'}), 400
        else:
            return jsonify({'success': False, 'error': 'Erro ao cadastrar'}), 400
    except Exception as e:
        logger.error(f"Erro ao cadastrar usuário: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/triagem')
@login_required
def triagem():
    """Página de triagem com dados do usuário no navbar"""
    user_data = None
    if 'user_id' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT u.Nome_user, u.foto, c.cargo_nome, c.cod_cargo
            FROM usuario u
            JOIN cargo c ON u.cod_cargo = c.cod_cargo
            WHERE u.cod_usuario = %s
        ''', (session['user_id'],))
        
        user_data = cursor.fetchone()
        
        # Ajustar foto
        if user_data and user_data.get('foto'):
            if not user_data['foto'].startswith('data:'):
                if '.' in user_data['foto']:
                    user_data['foto'] = f"/static/uploads/avatars/{user_data['foto']}"
                else:
                    user_data['foto'] = f"data:image/jpeg;base64,{user_data['foto']}"
        elif user_data:
            user_data['foto'] = '/static/images/default-avatar-image.jpg'
        
        cursor.close()
        conn.close()
    
    return render_template('triagem.html', user=user_data)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Verificar se API está funcionando"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': True,
        'total_symptoms': len(symptom_columns),
        'total_categories': len(encoder.classes_),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/symptoms', methods=['GET'])
def get_symptoms():
    """Retornar lista de todos os sintomas disponíveis (traduzidos)"""
    search = request.args.get('search', '').lower()
    
    # Criar lista de sintomas com tradução
    symptoms_with_translation = []
    for symptom in symptom_columns:
        traducao = traduzir_sintoma(symptom)
        symptoms_with_translation.append({
            'original': symptom,
            'traducao': traducao,
            'display': f"{traducao} ({symptom})" if traducao != symptom else symptom
        })
    
    # Filtrar se houver busca
    if search:
        filtered = [s for s in symptoms_with_translation 
                   if search in s['original'].lower() or search in s['traducao'].lower()]
        return jsonify({
            'success': True,
            'total': len(filtered),
            'symptoms': filtered,
            'search_term': search
        })
    
    return jsonify({
        'success': True,
        'total': len(symptoms_with_translation),
        'symptoms': symptoms_with_translation
    })

@app.route('/api/consulta/editar', methods=['POST'])
@login_required
def editar_consulta():
    try:
        data = request.get_json()
        cod_consulta = data.get('cod_consulta')
        novo_horario = data.get('novo_horario')
        novas_obs = data.get('observacoes')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE consulta 
        SET hora_consulta = %s, tipo_atendimento = %s
        WHERE cod_consulta = %s
        ''', (novo_horario, novas_obs, cod_consulta))

        cursor.close()
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Consulta atualizada!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Retornar todas as categorias de doenças"""
    return jsonify({
        'success': True,
        'total': len(encoder.classes_),
        'categories': sorted(encoder.classes_.tolist())
    })

@app.route('/api/predict', methods=['POST'])
def predict():
    """
    Endpoint principal para predição
    
    Body JSON:
    {
        "symptoms": {
            "cough": 1,
            "fever": 1,
            "headache": 0
        },
        "top_k": 5  // opcional, default = 5
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'symptoms' not in data:
            return jsonify({
                'success': False,
                'error': 'Campo "symptoms" é obrigatório no body JSON'
            }), 400
        
        symptoms = data['symptoms']
        top_k = data.get('top_k', 5)
        
        if not isinstance(symptoms, dict):
            return jsonify({
                'success': False,
                'error': 'Campo "symptoms" deve ser um objeto/dicionário'
            }), 400
        
        if not symptoms:
            return jsonify({
                'success': False,
                'error': 'Pelo menos um sintoma deve ser fornecido'
            }), 400
        
        # Fazer predição
        result = predict_disease_category(symptoms, top_k)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Erro no endpoint /predict: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/solicitar-triagem')
@login_required
def solicitar_triagem_page():
    """Página para solicitar triagem"""
    if session.get('cod_cargo') != 'C002':
        return redirect('/login')
    return render_template('solicitar-triagem.html')

@app.route('/api/solicitar-triagem', methods=['POST'])
@login_required
def solicitar_triagem():
    """API para criar solicitação de triagem"""
    try:
        data = request.get_json()
        
        data_triagem = data.get('data_triagem')
        hora_triagem = data.get('hora_triagem')
        sintomas = data.get('sintomas', '')
        
        # Validar sintomas
        if not sintomas or len(sintomas) < 50:
            return jsonify({
                'success': False,
                'error': 'Descreva seus sintomas com mais detalhes (mínimo 50 caracteres)'
            }), 400
        
        # Validações de data...
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Gerar código
        cursor.execute('SELECT MAX(CAST(SUBSTRING(cod_consulta, 2) AS UNSIGNED)) FROM consulta')
        result = cursor.fetchone()
        last_id = list(result.values())[0] if result and list(result.values())[0] else 0
        novo_cod = f'C{str(last_id + 1).zfill(3)}'
        
        # Buscar convênio
        cursor.execute('SELECT cod_convenio FROM convenio LIMIT 1')
        convenio = cursor.fetchone()
        cod_convenio = convenio['cod_convenio'] if convenio else 'CV001'
        
        # Inserir sem médico
        cursor.execute('''
        INSERT INTO consulta 
        (cod_consulta, data_consulta, hora_consulta, tipo_atendimento, 
        status_consulta, cod_medico, cod_usuario, cod_convenio, local_consulta, sintomas_triagem)
        VALUES (%s, %s, %s, 'Triagem', 'Aguardando Triagem', NULL, %s, %s, 'Sala de Triagem', %s)
    ''', (novo_cod, data_triagem, hora_triagem, session['user_id'], cod_convenio, sintomas))
        
        # Salvar sintomas em outra tabela ou campo
        # (você pode adicionar um campo `sintomas_triagem` na tabela consulta)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Triagem solicitada com sucesso!',
            'cod_consulta': novo_cod
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao solicitar triagem: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
        
@app.route('/api/upload-foto', methods=['POST'])
@login_required
def upload_foto():
    """Upload de foto convertida para Base64"""
    try:
        import base64
        
        logger.info(f"Upload iniciado pelo usuário: {session['user_id']}")
        
        if 'foto' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhuma foto enviada'}), 400
        
        file = request.files['foto']
        
        if not file or file.filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Tipo de arquivo não permitido'}), 400
        
        # Converter para Base64
        foto_bytes = file.read()
        foto_base64 = base64.b64encode(foto_bytes).decode('utf-8')
        
        # Detectar tipo do arquivo
        extensao = file.filename.rsplit('.', 1)[1].lower()
        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif'
        }
        mime_type = mime_types.get(extensao, 'image/jpeg')
        
        # ✅ CRÍTICO: Adicionar "data:" no início
        foto_completa = f"data:{mime_type};base64,{foto_base64}"
        
        # Salvar no banco
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE usuario 
            SET foto = %s 
            WHERE cod_usuario = %s
        ''', (foto_completa, session['user_id']))
        #     ↑ AGORA COM "data:"
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Foto salva como Base64 no banco")
        
        return jsonify({
            'success': True, 
            'message': 'Foto atualizada com sucesso!',
            'foto_url': foto_completa  # ✅ Retornar completo
        })
        
    except Exception as e:
        logger.error(f"Erro no upload: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/foto-perfil', methods=['GET'])
@login_required
def get_foto_perfil():
    """Retornar foto do perfil como Data URL"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT foto FROM usuario WHERE cod_usuario = %s
        ''', (session['user_id'],))
        
        usuario = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if usuario and usuario['foto']:
            # Se já está no formato data:image/...;base64,
            if usuario['foto'].startswith('data:'):
                foto_url = usuario['foto']
            # Se está no formato antigo (nome de arquivo)
            elif '.' in usuario['foto']:
                foto_url = f"/static/uploads/avatars/{usuario['foto']}"
            # Se é só o base64 puro
            else:
                foto_url = f"data:image/jpeg;base64,{usuario['foto']}"
            
            return jsonify({'success': True, 'foto': foto_url})
        
        # Foto padrão se não tiver
        return jsonify({
            'success': True, 
            'foto': '/static/images/default-avatar-image.jpg'
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar foto: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    """Gerar PDF do relatório de análise"""
    try:
        data = request.get_json()
        
        if not data or 'predictions' not in data:
            return jsonify({
                'success': False,
                'error': 'Dados de predição são obrigatórios'
            }), 400
        
        # Criar PDF em memória
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=12,
            spaceBefore=12
        )
        normal_style = styles['Normal']
        
        # Título
        elements.append(Paragraph("🏥 Relatório de Análise de Sintomas", title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Informações do paciente (se fornecidas)
        if 'patient_info' in data:
            elements.append(Paragraph("📋 Informações do Paciente", heading_style))
            patient_data = [
                ['Nome:', data['patient_info'].get('name', 'Não informado')],
                ['Data:', data['patient_info'].get('date', datetime.now().strftime('%d/%m/%Y %H:%M'))],
            ]
            patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
            patient_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f7ff')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            elements.append(patient_table)
            elements.append(Spacer(1, 0.2*inch))
        
        # Sintomas Analisados
        elements.append(Paragraph("🔍 Sintomas Analisados", heading_style))
        symptoms_text = ", ".join(data['metadata']['symptoms_found_pt'])
        elements.append(Paragraph(f"<b>Total de sintomas:</b> {data['metadata']['total_symptoms_analyzed']}", normal_style))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph(f"<b>Sintomas identificados:</b> {symptoms_text}", normal_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Resultados da Predição
        elements.append(Paragraph("📊 Categorias de Doenças Identificadas", heading_style))
        
        # Tabela de resultados
        table_data = [['#', 'Categoria', 'Probabilidade', 'Confiança']]
        for idx, pred in enumerate(data['predictions'], 1):
            table_data.append([
                str(idx),
                pred['category_pt'],
                pred['percentage'],
                pred['confidence_pt']
            ])
        
        results_table = Table(table_data, colWidths=[0.5*inch, 3*inch, 1.5*inch, 1.5*inch])
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        elements.append(results_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Detalhes técnicos
        elements.append(Paragraph("ℹ️ Detalhes Técnicos", heading_style))
        tech_data = [
            ['Timestamp:', data['metadata']['timestamp']],
            ['Sintomas reconhecidos:', str(len(data['metadata']['symptoms_found']))],
            ['Modelo utilizado:', 'Random Forest Classifier']
        ]
        tech_table = Table(tech_data, colWidths=[2*inch, 4*inch])
        tech_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(tech_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Aviso médico
        elements.append(Spacer(1, 0.5*inch))
        disclaimer = Paragraph(
            "<b>⚠️ AVISO IMPORTANTE:</b> Este relatório é gerado por um sistema de inteligência artificial "
            "e tem caráter informativo. NÃO substitui consulta médica profissional. "
            "Em caso de sintomas persistentes ou graves, procure um médico imediatamente.",
            ParagraphStyle('Disclaimer', parent=normal_style, textColor=colors.red, fontSize=9, alignment=TA_CENTER)
        )
        elements.append(disclaimer)
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Retornar PDF
        from flask import send_file
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'relatorio_analise_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
@app.route('/api/diseases-by-category/<category>', methods=['GET'])
def get_diseases_by_category(category):
    """Retornar doenças de uma categoria específica"""
    if category in disease_categories:
        return jsonify({
            'success': True,
            'category': category,
            'total_diseases': len(disease_categories[category]),
            'diseases': sorted(disease_categories[category])
        })
    else:
        return jsonify({
            'success': False,
            'error': f'Categoria "{category}" não encontrada'
        }), 404

@app.route('/api/notificacoes', methods=['GET'])
@login_required
def get_notificacoes():
    """Buscar notificações do usuário logado"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT cod_notificacao, tipo_notificacao, titulo, mensagem, 
                   lida, data_criacao, cod_consulta
            FROM notificacao
            WHERE cod_usuario_destino = %s
            ORDER BY data_criacao DESC
            LIMIT 20
        ''', (session['user_id'],))
        
        notificacoes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'notificacoes': notificacoes
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar notificações: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/notificacoes/marcar-lidas', methods=['POST'])
@login_required
def marcar_notificacoes_lidas():
    """Marcar todas as notificações como lidas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE notificacao
            SET lida = TRUE
            WHERE cod_usuario_destino = %s AND lida = FALSE
        ''', (session['user_id'],))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Notificações marcadas como lidas'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
        
@app.route('/api/medico/encaminhamentos', methods=['GET'])
@login_required
def get_encaminhamentos_medico():
    """Buscar encaminhamentos de triagem para o médico"""
    try:
        if session.get('cod_cargo') not in ['C001', 'C005']:
            return jsonify({'success': False, 'error': 'Acesso restrito a médicos'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar especialidade do médico
        cursor.execute('''
            SELECT especialidade FROM medico 
            WHERE cod_usuario = %s
        ''', (session['user_id'],))
        
        medico_data = cursor.fetchone()
        if not medico_data:
            return jsonify({'success': False, 'error': 'Médico não encontrado'}), 404
        
        especialidade_medico = medico_data['especialidade']
        
        # Buscar triagens CONCLUÍDAS que correspondem à especialidade do médico
        # e que ainda NÃO têm médico atribuído (status = Aguardando Consulta)
        cursor.execute('''
            SELECT 
                c.cod_consulta,
                u.Nome_user as paciente,
                c.sintomas_descritos as sintomas,
                t.categoria_ia,
                t.probabilidade_ia as probabilidade,
                t.data_triagem,
                t.relatorio_ia_json
            FROM consulta c
            JOIN usuario u ON c.cod_usuario = u.cod_usuario
            JOIN triagem t ON c.cod_consulta = t.cod_consulta
            WHERE c.status_consulta = 'Aguardando Consulta'
            AND c.cod_medico IS NULL
            AND t.categoria_ia IS NOT NULL
            ORDER BY t.data_triagem DESC
            LIMIT 10
        ''')
        
        encaminhamentos_raw = cursor.fetchall()
        
        # Filtrar apenas os que correspondem à especialidade do médico
        encaminhamentos = []
        for enc in encaminhamentos_raw:
            categoria_ia = enc['categoria_ia']
            especialidade_sugerida = CATEGORIA_PARA_ESPECIALIDADE.get(categoria_ia, 'Clínico Geral')
            
            # Se a especialidade bate ou se o médico é Clínico Geral (aceita tudo)
            if especialidade_medico == especialidade_sugerida or especialidade_medico == 'Clínico Geral':
                encaminhamentos.append({
                    'cod_consulta': enc['cod_consulta'],
                    'paciente': enc['paciente'],
                    'sintomas': enc['sintomas'][:200] + '...' if len(enc['sintomas']) > 200 else enc['sintomas'],
                    'categoria_ia': enc['categoria_ia'],
                    'probabilidade': float(enc['probabilidade']) if enc['probabilidade'] else 0,
                    'data_triagem': enc['data_triagem'].strftime('%d/%m/%Y %H:%M') if enc['data_triagem'] else '-',
                    'relatorio_pdf': f'/api/relatorio-triagem/{enc["cod_consulta"]}'  # Link para baixar PDF
                })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'encaminhamentos': encaminhamentos
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar encaminhamentos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/medico/aceitar-encaminhamento', methods=['POST'])
@login_required
def aceitar_encaminhamento():
    """Médico aceita um encaminhamento de triagem"""
    try:
        # ✅ Permitir C001 (médico) e C005 (dev)
        if session.get('cod_cargo') not in ['C001', 'C005']:
            return jsonify({'success': False, 'error': 'Acesso restrito a médicos'}), 403
        
        data = request.get_json()
        cod_consulta = data.get('cod_consulta')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar cod_medico do usuário logado
        cursor.execute('''
            SELECT cod_medico FROM medico WHERE cod_usuario = %s
        ''', (session['user_id'],))
        
        medico = cursor.fetchone()
        if not medico:
            return jsonify({'success': False, 'error': 'Médico não encontrado'}), 404
        
        cod_medico = medico['cod_medico']
        
        # Atualizar consulta: atribuir médico e mudar status
        cursor.execute('''
            UPDATE consulta
            SET cod_medico = %s,
                status_consulta = 'Confirmada'
            WHERE cod_consulta = %s
            AND cod_medico IS NULL
        ''', (cod_medico, cod_consulta))
        
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'Consulta já foi atribuída a outro médico'}), 400
        
        # Criar notificação para o PACIENTE
        cursor.execute('SELECT cod_usuario FROM consulta WHERE cod_consulta = %s', (cod_consulta,))
        result = cursor.fetchone()
        cod_paciente = result['cod_usuario']
        
        cursor.execute('''
            INSERT INTO notificacao (cod_notificacao, tipo_notificacao, titulo, mensagem, cod_usuario_destino, cod_consulta)
            SELECT 
                CONCAT('N', LPAD(COALESCE(MAX(CAST(SUBSTRING(cod_notificacao, 2) AS UNSIGNED)), 0) + 1, 3, '0')),
                'Consulta Marcada',
                'Consulta Agendada',
                'Sua consulta foi agendada com o médico!',
                %s,
                %s
            FROM notificacao
        ''', (cod_paciente, cod_consulta))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Encaminhamento aceito com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"Erro ao aceitar encaminhamento: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/salvar-resultado-triagem', methods=['POST'])
@login_required
def salvar_resultado_triagem():
    """Salvar resultado da triagem (após análise da IA)"""
    try:
        data = request.get_json()
        
        cod_consulta = data.get('cod_consulta')
        categoria_ia = data.get('categoria_ia')  # Ex: 'Cardiovascular'
        probabilidade_ia = data.get('probabilidade_ia')  # Ex: 85.5
        sintomas_analisados = data.get('sintomas_analisados')  # JSON dos sintomas
        relatorio_json = data.get('relatorio_completo')  # JSON completo da análise
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar cod_enfermeiro do usuário logado
        cursor.execute('''
            SELECT cod_enfermeiro FROM enfermeiro WHERE cod_usuario = %s
        ''', (session['user_id'],))
        
        enfermeiro = cursor.fetchone()
        cod_enfermeiro = enfermeiro['cod_enfermeiro'] if enfermeiro else None
        
        # Gerar código de triagem
        cursor.execute('SELECT MAX(CAST(SUBSTRING(cod_triagem, 2) AS UNSIGNED)) FROM triagem')
        result = cursor.fetchone()
        last_id = list(result.values())[0] if result and list(result.values())[0] else 0
        novo_cod_triagem = f'T{str(last_id + 1).zfill(3)}'
        
        # Inserir registro na tabela triagem
        cursor.execute('''
            INSERT INTO triagem 
            (cod_triagem, cod_consulta, sintomas_relatados, categoria_ia, 
             probabilidade_ia, relatorio_ia_json, nivel_urgencia, 
             data_triagem, cod_enfermeiro)
            VALUES (%s, %s, %s, %s, %s, %s, 'Rotina', NOW(), %s)
        ''', (novo_cod_triagem, cod_consulta, sintomas_analisados, 
              categoria_ia, probabilidade_ia, json.dumps(relatorio_json), cod_enfermeiro))
        
        # Atualizar status da consulta
        cursor.execute('''
            UPDATE consulta
            SET status_consulta = 'Aguardando Consulta'
            WHERE cod_consulta = %s
        ''', (cod_consulta,))
        
        # Criar notificação para o PACIENTE
        cursor.execute('SELECT cod_usuario FROM consulta WHERE cod_consulta = %s', (cod_consulta,))
        result = cursor.fetchone()
        cod_paciente = result['cod_usuario']
        
        cursor.execute('''
            INSERT INTO notificacao (cod_notificacao, tipo_notificacao, titulo, mensagem, cod_usuario_destino, cod_consulta)
            SELECT 
                CONCAT('N', LPAD(COALESCE(MAX(CAST(SUBSTRING(cod_notificacao, 2) AS UNSIGNED)), 0) + 1, 3, '0')),
                'Resultado Disponível',
                'Triagem Concluída',
                'Sua triagem foi concluída. Em breve você será encaminhado para um especialista.',
                %s,
                %s
            FROM notificacao
        ''', (cod_paciente, cod_consulta))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Resultado da triagem salvo com sucesso!',
            'cod_triagem': novo_cod_triagem
        })
        
    except Exception as e:
        logger.error(f"Erro ao salvar resultado da triagem: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== ADICIONAR ESTAS ROTAS NO app.py ==========
# Adicione estas importações no topo do arquivo
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Armazenamento temporário de códigos (em produção, use Redis ou banco)
recovery_codes = {}

# ========== ROTAS DE RECUPERAÇÃO DE SENHA ==========

@app.route('/password')
def password_page():
    """Página de recuperação de senha"""
    return render_template('password.html')

@app.route('/password-code')
def password_code_page():
    """Página de código de verificação"""
    return render_template('password-code.html')

@app.route('/api/solicitar-codigo', methods=['POST'])
def solicitar_codigo():
    """Solicitar código de recuperação de senha"""
    try:
        data = request.get_json()
        cpf = data.get('cpf', '').replace('.', '').replace('-', '')
        email = data.get('email', '').lower().strip()
        
        if not cpf or not email:
            return jsonify({'success': False, 'error': 'CPF e email são obrigatórios'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se usuário existe
        cursor.execute('''
            SELECT cod_usuario, Nome_user 
            FROM usuario 
            WHERE CPF = %s AND email = %s
        ''', (cpf, email))
        
        usuario = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not usuario:
            return jsonify({
                'success': False, 
                'error': 'CPF ou email não encontrados'
            }), 404
        
        # Gerar código de 4 dígitos
        codigo = ''.join([str(secrets.randbelow(10)) for _ in range(4)])
        
        # Armazenar código com expiração de 10 minutos
        recovery_codes[email] = {
            'codigo': codigo,
            'cpf': cpf,
            'expira': datetime.now() + timedelta(minutes=10),
            'tentativas': 0
        }
        
        # Enviar email (simulado - configure SMTP real em produção)
        logger.info(f"📧 Código de recuperação para {email}: {codigo}")
        
        # TODO: Implementar envio real de email
        # enviar_email_recuperacao(email, codigo, usuario['Nome_user'])
        
        return jsonify({
            'success': True,
            'message': 'Código enviado para seu email',
            'debug_code': codigo  # REMOVER EM PRODUÇÃO!
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao solicitar código: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/verificar-codigo', methods=['POST'])
def verificar_codigo():
    """Verificar código de recuperação"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        codigo_digitado = data.get('codigo', '')
        
        if not email or not codigo_digitado:
            return jsonify({'success': False, 'error': 'Email e código são obrigatórios'}), 400
        
        # Verificar se existe código para este email
        if email not in recovery_codes:
            return jsonify({
                'success': False,# Continuação do @app.route('/api/verificar-codigo')
                'error': 'Código não encontrado ou expirado. Solicite um novo código.'
            }), 404
        
        dados_codigo = recovery_codes[email]
        
        # Verificar expiração
        if datetime.now() > dados_codigo['expira']:
            del recovery_codes[email]
            return jsonify({
                'success': False,
                'error': 'Código expirado. Solicite um novo código.'
            }), 400
        
        # Verificar tentativas
        if dados_codigo['tentativas'] >= 3:
            del recovery_codes[email]
            return jsonify({
                'success': False,
                'error': 'Muitas tentativas incorretas. Solicite um novo código.'
            }), 400
        
        # Verificar código
        if codigo_digitado != dados_codigo['codigo']:
            recovery_codes[email]['tentativas'] += 1
            return jsonify({
                'success': False,
                'error': f'Código incorreto. Tentativas restantes: {3 - recovery_codes[email]["tentativas"]}'
            }), 400
        
        # Código correto - gerar token temporário
        token = secrets.token_urlsafe(32)
        recovery_codes[email]['token'] = token
        
        return jsonify({
            'success': True,
            'message': 'Código verificado com sucesso',
            'token': token
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao verificar código: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/redefinir-senha', methods=['POST'])
def redefinir_senha():
    """Redefinir senha após verificação do código"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        token = data.get('token', '')
        nova_senha = data.get('nova_senha', '')
        confirma_senha = data.get('confirma_senha', '')
        
        # Validações
        if not all([email, token, nova_senha, confirma_senha]):
            return jsonify({'success': False, 'error': 'Todos os campos são obrigatórios'}), 400
        
        if nova_senha != confirma_senha:
            return jsonify({'success': False, 'error': 'As senhas não coincidem'}), 400
        
        if len(nova_senha) < 6:
            return jsonify({'success': False, 'error': 'Senha deve ter no mínimo 6 caracteres'}), 400
        
        # Verificar token
        if email not in recovery_codes or recovery_codes[email].get('token') != token:
            return jsonify({'success': False, 'error': 'Token inválido ou expirado'}), 401
        
        cpf = recovery_codes[email]['cpf']
        
        # Atualizar senha no banco
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE usuario
            SET senha = %s
            WHERE CPF = %s AND email = %s
        ''', (hash_senha(nova_senha), cpf, email))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Limpar código usado
        del recovery_codes[email]
        
        return jsonify({
            'success': True,
            'message': 'Senha redefinida com sucesso!'
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao redefinir senha: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    

@app.route('/settings')
@login_required
def settings_page():
    """Página de configurações do usuário"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar dados completos do usuário
        cursor.execute('''
            SELECT u.*, c.cargo_nome
            FROM usuario u
            JOIN cargo c ON u.cod_cargo = c.cod_cargo
            WHERE u.cod_usuario = %s
        ''', (session['user_id'],))
        
        usuario = cursor.fetchone()
        
        if not usuario:
            cursor.close()
            conn.close()
            return redirect('/login')
        
        # Ajustar foto
        if usuario.get('foto'):
            if usuario['foto'].startswith('data:'):
                pass
            elif '.' in usuario['foto']:
                usuario['foto'] = f"/static/uploads/avatars/{usuario['foto']}"
            else:
                usuario['foto'] = f"data:image/jpeg;base64,{usuario['foto']}"
        else:
            usuario['foto'] = '/static/images/default-avatar-image.jpg'
        
        # Formatar data de nascimento
        if usuario.get('data_nasc'):
            usuario['data_nasc'] = usuario['data_nasc'].strftime('%Y-%m-%d')
        
        # Verificar se pode excluir conta (não ter consultas futuras)
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM consulta
            WHERE cod_usuario = %s
            AND data_consulta >= CURDATE()
            AND status_consulta NOT IN ('Cancelada', 'Concluída')
        ''', (session['user_id'],))
        
        consultas_futuras = cursor.fetchone()
        usuario['pode_excluir'] = consultas_futuras['total'] == 0
        usuario['consultas_futuras'] = consultas_futuras['total']
        
        cursor.close()
        conn.close()
        
        return render_template('settings.html', usuario=usuario)
        
    except Exception as e:
        logger.error(f"Erro ao carregar settings: {str(e)}")
        return redirect('/perfil-paciente')


@app.route('/api/settings/atualizar-info', methods=['POST'])
@login_required
def atualizar_informacoes():
    """Atualizar informações pessoais do usuário"""
    try:
        data = request.get_json()
        
        nome = data.get('nome', '').strip()
        email = data.get('email', '').strip()
        telefone = data.get('telefone', '').strip()
        data_nasc = data.get('data_nasc')
        bio = data.get('bio', '').strip()
        
        # Validações
        if not nome or len(nome) < 3:
            return jsonify({'success': False, 'error': 'Nome deve ter no mínimo 3 caracteres'}), 400
        
        if not email or '@' not in email:
            return jsonify({'success': False, 'error': 'Email inválido'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se email já existe (exceto o próprio usuário)
        cursor.execute('''
            SELECT cod_usuario FROM usuario 
            WHERE email = %s AND cod_usuario != %s
        ''', (email, session['user_id']))
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Email já cadastrado por outro usuário'}), 400
        
        # Atualizar dados
        cursor.execute('''
            UPDATE usuario
            SET Nome_user = %s, 
                email = %s, 
                telefone = %s, 
                data_nasc = %s
            WHERE cod_usuario = %s
        ''', (nome, email, telefone, data_nasc, session['user_id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Atualizar session
        session['user_nome'] = nome
        session['user_email'] = email
        
        return jsonify({
            'success': True,
            'message': 'Informações atualizadas com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"Erro ao atualizar informações: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings/alterar-senha', methods=['POST'])
@login_required
def alterar_senha():
    """Alterar senha do usuário"""
    try:
        data = request.get_json()
        
        senha_atual = data.get('senha_atual')
        nova_senha = data.get('nova_senha')
        confirma_senha = data.get('confirma_senha')
        
        # Validações
        if not all([senha_atual, nova_senha, confirma_senha]):
            return jsonify({'success': False, 'error': 'Todos os campos são obrigatórios'}), 400
        
        if nova_senha != confirma_senha:
            return jsonify({'success': False, 'error': 'As senhas não coincidem'}), 400
        
        if len(nova_senha) < 6:
            return jsonify({'success': False, 'error': 'Nova senha deve ter no mínimo 6 caracteres'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar senha atual
        cursor.execute('''
            SELECT senha FROM usuario WHERE cod_usuario = %s
        ''', (session['user_id'],))
        
        usuario = cursor.fetchone()
        
        if not usuario or usuario['senha'] != hash_senha(senha_atual):
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Senha atual incorreta'}), 401
        
        # Atualizar senha
        cursor.execute('''
            UPDATE usuario
            SET senha = %s
            WHERE cod_usuario = %s
        ''', (hash_senha(nova_senha), session['user_id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Senha alterada com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"Erro ao alterar senha: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings/notificacoes', methods=['GET', 'POST'])
@login_required
def gerenciar_notificacoes():
    """Gerenciar preferências de notificações"""
    try:
        if request.method == 'GET':
            # Buscar preferências atuais
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Criar tabela de preferências se não existir
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preferencias_notificacao (
                    cod_usuario VARCHAR(10) PRIMARY KEY,
                    email_notif BOOLEAN DEFAULT TRUE,
                    sms_notif BOOLEAN DEFAULT TRUE,
                    clinic_notif BOOLEAN DEFAULT FALSE,
                    appointment_notif BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (cod_usuario) REFERENCES usuario(cod_usuario)
                )
            ''')
            
            # Buscar ou criar preferências
            cursor.execute('''
                SELECT * FROM preferencias_notificacao WHERE cod_usuario = %s
            ''', (session['user_id'],))
            
            prefs = cursor.fetchone()
            
            if not prefs:
                # Criar preferências padrão
                cursor.execute('''
                    INSERT INTO preferencias_notificacao (cod_usuario)
                    VALUES (%s)
                ''', (session['user_id'],))
                conn.commit()
                
                prefs = {
                    'email_notif': True,
                    'sms_notif': True,
                    'clinic_notif': False,
                    'appointment_notif': True
                }
            
            cursor.close()
            conn.close()
            
            return jsonify({'success': True, 'preferencias': prefs})
        
        else:  # POST
            data = request.get_json()
            
            email_notif = data.get('email_notif', False)
            sms_notif = data.get('sms_notif', False)
            clinic_notif = data.get('clinic_notif', False)
            appointment_notif = data.get('appointment_notif', False)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Atualizar ou inserir preferências
            cursor.execute('''
                INSERT INTO preferencias_notificacao 
                (cod_usuario, email_notif, sms_notif, clinic_notif, appointment_notif)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    email_notif = %s,
                    sms_notif = %s,
                    clinic_notif = %s,
                    appointment_notif = %s
            ''', (session['user_id'], email_notif, sms_notif, clinic_notif, appointment_notif,
                  email_notif, sms_notif, clinic_notif, appointment_notif))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Preferências de notificação atualizadas!'
            })
        
    except Exception as e:
        logger.error(f"Erro ao gerenciar notificações: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings/enviar-suporte', methods=['POST'])
@login_required
def enviar_suporte():
    """Enviar mensagem para o suporte"""
    try:
        data = request.get_json()
        
        assunto = data.get('assunto', '').strip()
        mensagem = data.get('mensagem', '').strip()
        
        if not assunto or not mensagem:
            return jsonify({'success': False, 'error': 'Assunto e mensagem são obrigatórios'}), 400
        
        if len(mensagem) < 20:
            return jsonify({'success': False, 'error': 'Mensagem muito curta (mínimo 20 caracteres)'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Criar tabela de suporte se não existir
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mensagem_suporte (
                id_mensagem INT AUTO_INCREMENT PRIMARY KEY,
                cod_usuario VARCHAR(10),
                assunto VARCHAR(200),
                mensagem TEXT,
                status ENUM('Pendente', 'Em Análise', 'Resolvido') DEFAULT 'Pendente',
                data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cod_usuario) REFERENCES usuario(cod_usuario)
            )
        ''')
        
        # Inserir mensagem
        cursor.execute('''
            INSERT INTO mensagem_suporte (cod_usuario, assunto, mensagem)
            VALUES (%s, %s, %s)
        ''', (session['user_id'], assunto, mensagem))
        
        conn.commit()
        
        # Buscar email do usuário para log
        cursor.execute('SELECT email, Nome_user FROM usuario WHERE cod_usuario = %s', (session['user_id'],))
        usuario = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        logger.info(f"📧 Mensagem de suporte de {usuario['Nome_user']} ({usuario['email']})")
        logger.info(f"   Assunto: {assunto}")
        logger.info(f"   Mensagem: {mensagem[:100]}...")
        
        return jsonify({
            'success': True,
            'message': 'Mensagem enviada com sucesso! Responderemos em breve.'
        })
        
    except Exception as e:
        logger.error(f"Erro ao enviar suporte: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings/excluir-conta', methods=['POST'])
@login_required
def excluir_conta():
    """Excluir conta do usuário (apenas se não tiver consultas futuras)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar consultas futuras
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM consulta
            WHERE cod_usuario = %s
            AND data_consulta >= CURDATE()
            AND status_consulta NOT IN ('Cancelada', 'Concluída')
        ''', (session['user_id'],))
        
        result = cursor.fetchone()
        
        if result['total'] > 0:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Você ainda tem {result["total"]} consulta(s) agendada(s). Cancele-as antes de excluir a conta.'
            }), 400
        
        # Buscar dados do usuário para log
        cursor.execute('SELECT Nome_user, email FROM usuario WHERE cod_usuario = %s', (session['user_id'],))
        usuario = cursor.fetchone()
        
        # Excluir dados relacionados primeiro (por causa das foreign keys)
        cursor.execute('DELETE FROM preferencias_notificacao WHERE cod_usuario = %s', (session['user_id'],))
        cursor.execute('DELETE FROM notificacao WHERE cod_usuario_destino = %s', (session['user_id'],))
        cursor.execute('DELETE FROM mensagem_suporte WHERE cod_usuario = %s', (session['user_id'],))
        
        # Excluir usuário
        cursor.execute('DELETE FROM usuario WHERE cod_usuario = %s', (session['user_id'],))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"🗑️ Conta excluída: {usuario['Nome_user']} ({usuario['email']})")
        
        # Limpar sessão
        session.clear()
        
        return jsonify({
            'success': True,
            'message': 'Conta excluída com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"Erro ao excluir conta: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
        
@app.route('/api/relatorio-triagem/<cod_consulta>', methods=['GET'])
@login_required
def download_relatorio_triagem(cod_consulta):
    """Download do relatório PDF da triagem"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar dados da triagem
        cursor.execute('''
            SELECT t.*, u.Nome_user as paciente, c.sintomas_descritos
            FROM triagem t
            JOIN consulta c ON t.cod_consulta = c.cod_consulta
            JOIN usuario u ON c.cod_usuario = u.cod_usuario
            WHERE t.cod_consulta = %s
        ''', (cod_consulta,))
        
        triagem = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not triagem:
            return jsonify({'success': False, 'error': 'Triagem não encontrada'}), 404
        
        # Parsear JSON do relatório
        relatorio_json = json.loads(triagem['relatorio_ia_json']) if triagem['relatorio_ia_json'] else {}
        
        # Criar PDF usando a mesma estrutura do /api/generate-pdf
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        elements = []
        
        # [Adicionar aqui a mesma lógica de geração de PDF do /api/generate-pdf]
        # Mas usando os dados de `triagem` e `relatorio_json`
        
        # ... (código igual ao generate_pdf, adaptando para os dados da triagem)
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'relatorio_triagem_{cod_consulta}.pdf'
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
# ========== INICIAR SERVIDOR ==========
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 LOTUS CLINIC - API COMPLETA")
    print("="*60)
    print(f"✅ Banco de dados: Inicializado")
    print(f"✅ Modelo IA: {len(symptom_columns)} sintomas")
    print(f"✅ Categorias: {len(encoder.classes_)}")
    print("\n📍 Endpoints disponíveis:")
    print("   GET  /login - Página de login")
    print("   GET  /register - Página de cadastro")
    print("   POST /api/login - Fazer login")
    print("   POST /api/register - Cadastrar usuário")
    print("   POST /api/logout - Fazer logout")
    print("   GET  /triagem - Sistema de triagem (requer login)")
    print("   POST /api/predict - Análise de sintomas (requer login)")
    print("\n🌐 Servidor: http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
# FIM DO ARQUIVO - NÃO ADICIONE NADA ABAIXO DESTA LINHA
    
    