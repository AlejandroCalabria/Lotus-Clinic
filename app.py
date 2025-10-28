from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for
from flask_cors import CORS
import pickle
import json
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
import sqlite3
import hashlib
import os
from werkzeug.utils import secure_filename
from functools import wraps
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
def init_db():
    """Inicializa o banco de dados SQLite"""
    conn = sqlite3.connect('lotus_clinic.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            telefone TEXT NOT NULL,
            cep TEXT NOT NULL,
            data_nascimento DATE NOT NULL,
            senha_hash TEXT NOT NULL,
            avatar TEXT,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultimo_login TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ Banco de dados inicializado!")

# Inicializar DB ao iniciar aplicação
init_db()

def hash_senha(senha):
    """Gera hash SHA256 da senha"""
    return hashlib.sha256(senha.encode()).hexdigest()

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
        
        # Processar avatar
        avatar_filename = None
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{cpf}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                avatar_filename = filename
        
        # Salvar no banco
        conn = sqlite3.connect('lotus_clinic.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO usuarios (nome, cpf, email, telefone, cep, data_nascimento, senha_hash, avatar)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nome, cpf, email, telefone, cep, data_nascimento, hash_senha(senha), avatar_filename))
            
            conn.commit()
            user_id = cursor.lastrowid
            
            # Fazer login automático
            session['user_id'] = user_id
            session['user_nome'] = nome
            session['user_email'] = email
            
            return jsonify({
                'success': True,
                'message': 'Cadastro realizado com sucesso!',
                'redirect': '/triagem'
            }), 201
            
        except sqlite3.IntegrityError as e:
            if 'cpf' in str(e):
                return jsonify({'success': False, 'error': 'CPF já cadastrado'}), 400
            elif 'email' in str(e):
                return jsonify({'success': False, 'error': 'Email já cadastrado'}), 400
            else:
                return jsonify({'success': False, 'error': 'Erro ao cadastrar usuário'}), 400
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Erro no registro: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Fazer login"""
    try:
        data = request.get_json()
        email = data.get('email')
        senha = data.get('senha')
        
        if not email or not senha:
            return jsonify({'success': False, 'error': 'Email e senha são obrigatórios'}), 400
        
        conn = sqlite3.connect('lotus_clinic.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, nome, email, senha_hash, avatar 
            FROM usuarios 
            WHERE email = ?
        ''', (email,))
        
        user = cursor.fetchone()
        
        if user and user[3] == hash_senha(senha):
            # Login bem-sucedido
            session['user_id'] = user[0]
            session['user_nome'] = user[1]
            session['user_email'] = user[2]
            session['user_avatar'] = user[4]
            
            # Atualizar último login
            cursor.execute('''
                UPDATE usuarios 
                SET ultimo_login = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (user[0],))
            conn.commit()
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Login realizado com sucesso!',
                'user': {
                    'nome': user[1],
                    'email': user[2],
                    'avatar': user[4]
                },
                'redirect': '/triagem'
            }), 200
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Email ou senha inválidos'}), 401
            
    except Exception as e:
        logger.error(f"Erro no login: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """Fazer logout"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logout realizado com sucesso'}), 200

@app.route('/api/current-user', methods=['GET'])
@login_required
def current_user():
    """Retornar dados do usuário logado"""
    return jsonify({
        'success': True,
        'user': {
            'id': session.get('user_id'),
            'nome': session.get('user_nome'),
            'email': session.get('user_email'),
            'avatar': session.get('user_avatar')
        }
    }), 200

# ========== ROTAS DA API ==========
@app.route('/')
def index():
    return redirect(url_for('login_page'))

@app.route('/triagem')
@login_required
def triagem():
    return render_template('triagem.html')

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