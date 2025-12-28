#!/usr/bin/env python
# coding: utf-8

# In[8]:


import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
import json
import pickle

# ========== PASSO 1: CATEGORIZAÇÃO DAS DOENÇAS ==========
# Dicionário de categorização (você pode ajustar conforme necessário)
disease_categories = {
    # RESPIRATÓRIAS
    'Respiratory': [
        'asthma', 'emphysema', 'chronic obstructive pulmonary disease (copd)',
        'acute bronchitis', 'acute bronchiolitis', 'acute bronchospasm',
        'pneumonia', 'atelectasis', 'pulmonary congestion', 'pulmonary eosinophilia',
        'pulmonary fibrosis', 'pulmonary embolism', 'pulmonary hypertension',
        'acute respiratory distress syndrome (ards)', 'interstitial lung disease',
        'lung contusion', 'abscess of the lung', 'empyema', 'pleural effusion',
        'pneumothorax', 'lung cancer', 'croup', 'whooping cough', 'common cold',
        'acute sinusitis', 'chronic sinusitis', 'pharyngitis', 'laryngitis',
        'tracheitis', 'herpangina', 'obstructive sleep apnea (osa)'
    ],
    
    # CARDIOVASCULARES
    'Cardiovascular': [
        'heart attack', 'heart failure', 'angina', 'ischemic heart disease',
        'coronary atherosclerosis', 'atrial fibrillation', 'atrial flutter',
        'heart block', 'arrhythmia', 'cardiomyopathy', 'hypertrophic obstructive cardiomyopathy (hocm)',
        'pericarditis', 'endocarditis', 'hypertensive heart disease',
        'mitral valve disease', 'aortic valve disease', 'pulmonic valve disease',
        'tricuspid valve disease', 'congenital heart defect', 'heart contusion',
        'cardiac arrest', 'premature ventricular contractions (pvcs)',
        'premature atrial contractions (pacs)', 'paroxysmal ventricular tachycardia',
        'paroxysmal supraventricular tachycardia', 'sick sinus syndrome',
        'sinus bradycardia', 'hypertension of pregnancy', 'malignant hypertension'
    ],
    
    # GASTROINTESTINAIS
    'Gastrointestinal': [
        'gastroesophageal reflux disease (gerd)', 'gastritis', 'gastroduodenal ulcer',
        'infectious gastroenteritis', 'noninfectious gastroenteritis', 'indigestion',
        'irritable bowel syndrome', 'inflammatory bowel disease', 'crohn disease',
        'ulcerative colitis', 'diverticulosis', 'diverticulitis', 'intestinal obstruction',
        'intussusception', 'volvulus', 'ischemia of the bowel', 'intestinal malabsorption',
        'celiac disease', 'lactose intolerance', 'appendicitis', 'peritonitis',
        'gastrointestinal hemorrhage', 'hemorrhoids', 'anal fissure', 'anal fistula',
        'perirectal infection', 'rectal disorder', 'colorectal cancer', 'stomach cancer',
        'intestinal cancer', 'esophageal cancer', 'esophagitis', 'esophageal varices',
        'achalasia', 'stricture of the esophagus', 'hiatal hernia', 'abdominal hernia',
        'inguinal hernia', 'gastroparesis', 'dumping syndrome', 'ileus',
        'cholecystitis', 'choledocholithiasis', 'gallstone', 'ascending cholangitis',
        'acute pancreatitis', 'chronic pancreatitis', 'pancreatic cancer',
        'liver cancer', 'cirrhosis', 'nonalcoholic liver disease (nash)',
        'alcoholic liver disease', 'viral hepatitis', 'hepatitis due to a toxin',
        'hepatic encephalopathy', 'acute fatty liver of pregnancy (aflp)',
        'meckel diverticulum', 'zenker diverticulum', 'hirschsprung disease'
    ],
    
    # NEUROLÓGICAS
    'Neurological': [
        'stroke', 'transient ischemic attack', 'intracranial hemorrhage',
        'intracerebral hemorrhage', 'subarachnoid hemorrhage', 'subdural hemorrhage',
        'epidural hemorrhage', 'cerebral edema', 'migraine', 'tension headache',
        'headache after lumbar puncture', 'epilepsy', 'seizures',
        'parkinson disease', 'alzheimer disease', 'dementia', 'lewy body dementia',
        'multiple sclerosis', 'amyotrophic lateral sclerosis (als)',
        'guillain barre syndrome', 'myasthenia gravis', 'muscular dystrophy',
        'cerebral palsy', 'spina bifida', 'hydrocephalus', 'normal pressure hydrocephalus',
        'meningitis', 'encephalitis', 'brain cancer', 'meningioma', 'ependymoma',
        'bell palsy', 'trigeminal neuralgia', 'cranial nerve palsy', 'neuralgia',
        'peripheral nerve disorder', 'mononeuritis', 'brachial neuritis',
        'diabetic peripheral neuropathy', 'neuropathy due to drugs',
        'chronic inflammatory demyelinating polyneuropathy (cidp)',
        'nerve impingement near the shoulder', 'carpal tunnel syndrome',
        'sciatica', 'injury to the spinal cord', 'spinal stenosis', 'syringomyelia',
        'concussion', 'head injury', 'intracranial abscess', 'neurofibromatosis',
        'tuberous sclerosis', 'vertebrobasilar insufficiency', 'central atherosclerosis',
        'wernicke korsakoff syndrome', 'narcolepsy', 'restless leg syndrome',
        'essential tremor', 'myoclonus', 'extrapyramidal effect of drugs',
        'autonomic nervous system disorder', 'complex regional pain syndrome',
        'pseudotumor cerebri', 'moyamoya disease', 'friedrich ataxia',
        'spinocerebellar ataxia'
    ],
    
    # MUSCULOESQUELÉTICAS
    'Musculoskeletal': [
        'osteoarthritis', 'rheumatoid arthritis', 'arthritis of the hip',
        'juvenile rheumatoid arthritis', 'reactive arthritis', 'septic arthritis',
        'ankylosing spondylitis', 'gout', 'back pain', 'chronic back pain',
        'low back pain', 'lumbago', 'chronic knee pain', 'degenerative disc disease',
        'herniated disk', 'spondylosis', 'spondylitis', 'spondylolisthesis',
        'spinal stenosis', 'pain disorder affecting the neck', 'temporomandibular joint disorder',
        'jaw disorder', 'fracture of the hand', 'fracture of the arm',
        'fracture of the shoulder', 'fracture of the finger', 'fracture of the leg',
        'fracture of the foot', 'fracture of the ankle', 'fracture of the rib',
        'fracture of the patella', 'fracture of the neck', 'fracture of the vertebra',
        'fracture of the pelvis', 'fracture of the jaw', 'fracture of the skull',
        'fracture of the facial bones', 'dislocation of the elbow',
        'dislocation of the ankle', 'dislocation of the patella', 'dislocation of the foot',
        'dislocation of the knee', 'dislocation of the shoulder', 'dislocation of the hip',
        'dislocation of the wrist', 'dislocation of the vertebra', 'dislocation of the finger',
        'injury to the knee', 'injury to the hand', 'injury to the hip',
        'injury to the shoulder', 'injury to the arm', 'injury to the leg',
        'injury to the finger', 'injury to the ankle', 'injury to the face',
        'injury to the trunk', 'injury to the abdomen', 'injury to internal organ',
        'injury to the spinal cord', 'rotator cuff injury', 'knee ligament or meniscus tear',
        'tendinitis', 'bursitis', 'plantar fasciitis', 'lateral epicondylitis (tennis elbow)',
        'adhesive capsulitis of the shoulder', 'de quervain disease', 'trigger finger (finger disorder)',
        'carpal tunnel syndrome', 'chondromalacia of the patella', 'osteochondrosis',
        'osteoporosis', 'osteomyelitis', 'bone cancer', 'osteochondroma',
        'bone disorder', 'bone spur of the calcaneous', 'avascular necrosis',
        'fibromyalgia', 'polymyalgia rheumatica', 'myositis', 'myasthenia gravis',
        'muscle spasm', 'torticollis', 'scoliosis', 'bunion', 'hammer toe',
        'flat feet', 'ingrown toe nail', 'chronic pain disorder', 'pain after an operation'
    ],
    
    # INFECCIOSAS/PARASITÁRIAS
    'Infectious': [
        'sepsis', 'tuberculosis', 'hiv', 'viral hepatitis', 'mononucleosis',
        'flu', 'chickenpox', 'mumps', 'measles', 'rubella', 'dengue fever',
        'malaria', 'lyme disease', 'rocky mountain spotted fever', 'toxoplasmosis',
        'cat scratch disease', 'rabies', 'tetanus', 'botulism', 'anthrax',
        'gonorrhea', 'syphilis', 'chlamydia', 'genital herpes', 'hpv',
        'trichomoniasis', 'pelvic inflammatory disease', 'cervicitis',
        'urethritis', 'prostatitis', 'epididymitis', 'balanitis',
        'mastoiditis', 'acute otitis media', 'chronic otitis media', 'otitis externa (swimmer\'s ear)',
        'cellulitis or abscess of mouth', 'tooth abscess', 'peritonsillar abscess',
        'tonsillitis', 'tonsillar hypertrophy', 'conjunctivitis due to bacteria',
        'conjunctivitis due to virus', 'endophthalmitis', 'orbital cellulitis',
        'pyogenic skin infection', 'impetigo', 'cellulitis', 'erysipelas',
        'necrotizing fasciitis', 'lymphangitis', 'lymphadenitis', 'abscess of nose',
        'abscess of the pharynx', 'abscess of the lung', 'breast infection (mastitis)',
        'postoperative infection', 'infection of open wound', 'osteomyelitis',
        'septic arthritis', 'infectious gastroenteritis', 'viral exanthem',
        'scarlet fever', 'cold sore', 'shingles (herpes zoster)', 'oral thrush (yeast infection)',
        'yeast infection', 'vaginal yeast infection', 'fungal infection of the skin',
        'fungal infection of the hair', 'athlete\'s foot', 'onychomycosis',
        'aspergillosis', 'cryptococcosis', 'histoplasmosis', 'sporotrichosis',
        'valley fever', 'cysticercosis', 'trichinosis', 'pinworm infection',
        'parasitic disease', 'scabies', 'lice', 'acariasis', 'molluscum contagiosum',
        'viral warts', 'herpangina', 'whooping cough', 'croup'
    ],
    
    # ENDÓCRINAS/METABÓLICAS
    'Endocrine_Metabolic': [
        'diabetes', 'diabetic ketoacidosis', 'hyperosmotic hyperketotic state',
        'hypoglycemia', 'insulin overdose', 'gestational diabetes',
        'diabetic retinopathy', 'diabetic kidney disease', 'diabetic peripheral neuropathy',
        'hypothyroidism', 'hyperthyroidism', 'thyroid disease', 'thyroid nodule',
        'thyroid cancer', 'goiter', 'toxic multinodular goiter', 'graves disease',
        'hashimoto thyroiditis', 'subacute thyroiditis', 'pituitary disorder',
        'pituitary adenoma', 'cushing syndrome', 'glucocorticoid deficiency',
        'syndrome of inappropriate secretion of adh (siadh)', 'diabetes insipidus',
        'adrenal cancer', 'adrenal adenoma', 'parathyroid adenoma',
        'pseudohypoparathyroidism', 'hyperkalemia', 'hypokalemia', 'hypernatremia',
        'hyponatremia', 'hypercalcemia', 'hypocalcemia', 'magnesium deficiency',
        'hypercholesterolemia', 'hyperlipidemia', 'obesity', 'metabolic disorder',
        'amyloidosis', 'hemochromatosis', 'wilson disease', 'porphyria',
        'g6pd enzyme deficiency', 'gaucher disease', 'fabry disease',
        'protein deficiency', 'vitamin a deficiency', 'vitamin b12 deficiency',
        'vitamin d deficiency', 'folate deficiency', 'scurvy', 'iron deficiency anemia',
        'hormone disorder'
    ],
    
    # RENAIS/UROLÓGICAS
    'Renal_Urological': [
        'urinary tract infection', 'cystitis', 'pyelonephritis', 'urethritis',
        'prostatitis', 'epididymitis', 'acute kidney injury', 'kidney failure',
        'chronic kidney disease', 'primary kidney disease',
        'kidney disease due to longstanding hypertension', 'diabetic kidney disease',
        'polycystic kidney disease', 'kidney stone', 'hydronephrosis',
        'urinary tract obstruction', 'benign kidney cyst', 'kidney cancer',
        'bladder cancer', 'bladder disorder', 'bladder obstruction',
        'neurogenic bladder', 'atonic bladder', 'stress incontinence',
        'urge incontinence', 'overflow incontinence', 'benign prostatic hyperplasia (bph)',
        'prostate cancer', 'urethral stricture', 'urethral valves', 'urethral disorder',
        'vesicoureteral reflux', 'testicular cancer', 'testicular disorder',
        'testicular torsion', 'hydrocele of the testicle', 'varicocele of the testicles',
        'spermatocele', 'priapism', 'erectile dysfunction', 'cryptorchidism',
        'phimosis', 'peyronie disease'
    ],
    
    # GINECOLÓGICAS/OBSTÉTRICAS
    'Gynecological_Obstetric': [
        'pregnancy', 'problem during pregnancy', 'problems during pregnancy',
        'threatened pregnancy', 'ectopic pregnancy', 'gestational diabetes',
        'preeclampsia', 'hypertension of pregnancy', 'placenta previa',
        'placental abruption', 'premature rupture of amniotic membrane',
        'hyperemesis gravidarum', 'acute fatty liver of pregnancy (aflp)',
        'uterine contractions', 'induced abortion', 'spontaneous abortion',
        'missed abortion', 'postpartum depression', 'uterine fibroids',
        'endometriosis', 'endometrial hyperplasia', 'endometrial cancer',
        'uterine cancer', 'uterine atony', 'cervical cancer', 'cervical disorder',
        'cervicitis', 'ovarian cancer', 'ovarian cyst', 'ovarian torsion',
        'polycystic ovarian syndrome (pcos)', 'premature ovarian failure',
        'vaginitis', 'atrophic vaginitis', 'vaginal yeast infection',
        'trichomoniasis', 'bacterial vaginosis', 'pelvic inflammatory disease',
        'pelvic organ prolapse', 'pelvic fistula', 'vulvar disorder',
        'vulvar cancer', 'vulvodynia', 'vaginismus', 'female genitalia infection',
        'female infertility of unknown cause', 'menopause',
        'idiopathic absence of menstruation', 'idiopathic infrequent menstruation',
        'idiopathic irregular menstrual cycle', 'idiopathic excessive menstruation',
        'idiopathic painful menstruation', 'idiopathic nonmenstrual bleeding',
        'premenstrual tension syndrome', 'breast cancer', 'fibrocystic breast disease',
        'fibroadenoma', 'breast cyst', 'breast infection (mastitis)',
        'gynecomastia', 'galactorrhea of unknown cause'
    ],
    
    # PSIQUIÁTRICAS
    'Psychiatric': [
        'depression', 'dysthymic disorder', 'bipolar disorder', 'anxiety',
        'panic disorder', 'panic attack', 'social phobia', 'phobias',
        'post-traumatic stress disorder (ptsd)', 'acute stress reaction',
        'adjustment reaction', 'obsessive compulsive disorder (ocd)',
        'schizophrenia', 'psychotic disorder', 'schizoaffective disorder',
        'delusional disorder', 'substance-related mental disorder',
        'drug abuse', 'drug abuse (opioids)', 'drug abuse (cocaine)',
        'drug abuse (methamphetamine)', 'drug abuse (barbiturates)',
        'marijuana abuse', 'alcohol abuse', 'alcohol intoxication',
        'alcohol withdrawal', 'drug withdrawal', 'smoking or tobacco addiction',
        'eating disorder', 'anorexia nervosa', 'bulimia nervosa',
        'attention deficit hyperactivity disorder (adhd)', 'autism',
        'asperger syndrome', 'developmental disability', 'impulse control disorder',
        'conduct disorder', 'oppositional disorder', 'tic (movement) disorder',
        'tourette syndrome', 'conversion disorder', 'somatization disorder',
        'factitious disorder', 'dissociative disorder', 'personality disorder',
        'antisocial personality disorder', 'borderline personality disorder',
        'narcissistic personality disorder', 'neurosis', 'insomnia',
        'primary insomnia', 'sleep disorder', 'psychosexual disorder'
    ],
    
    # DERMATOLÓGICAS
    'Dermatological': [
        'acne', 'rosacea', 'eczema', 'psoriasis', 'seborrheic dermatitis',
        'contact dermatitis', 'dermatitis due to sun exposure', 'atopic dermatitis',
        'pityriasis rosea', 'lichen planus', 'lichen simplex', 'dyshidrosis',
        'intertrigo (skin condition)', 'skin cancer', 'melanoma', 'basal cell carcinoma',
        'squamous cell carcinoma', 'actinic keratosis', 'seborrheic keratosis',
        'skin growth', 'skin polyp', 'lipoma', 'sebaceous cyst', 'pilonidal cyst',
        'ganglion cyst', 'hemangioma', 'viral warts', 'molluscum contagiosum',
        'fungal infection of the skin', 'athlete\'s foot', 'onychomycosis',
        'tinea versicolor', 'cellulitis', 'impetigo', 'pyogenic skin infection',
        'abscess', 'furuncle', 'carbuncle', 'hidradenitis suppurativa',
        'decubitus ulcer', 'venous ulcer', 'diabetic ulcer', 'burn',
        'cold injury', 'frostbite', 'insect bite', 'envenomation from spider or animal bite',
        'scabies', 'lice', 'pediculosis', 'urticaria', 'angioedema',
        'erythema multiforme', 'stevens-johnson syndrome', 'pemphigus',
        'bullous pemphigoid', 'vitiligo', 'skin pigmentation disorder',
        'hyperpigmentation', 'hypopigmentation', 'alopecia', 'alopecia areata',
        'male pattern baldness', 'female pattern baldness', 'hirsutism',
        'hypertrichosis', 'hyperhidrosis', 'anhidrosis', 'nail disorder',
        'paronychia', 'ingrown toenail', 'callus', 'corn', 'wart',
        'skin tag', 'mole', 'atrophic skin condition', 'scar',
        'keloid', 'stretch marks'
    ],
    
    # OFTALMOLÓGICAS
    'Ophthalmological': [
        'cataract', 'glaucoma', 'acute glaucoma', 'chronic glaucoma',
        'macular degeneration', 'diabetic retinopathy',
        'retinopathy due to high blood pressure', 'retinal detachment',
        'central retinal artery or vein occlusion', 'vitreous hemorrhage',
        'vitreous degeneration', 'chorioretinitis', 'uveitis', 'iridocyclitis',
        'scleritis', 'conjunctivitis', 'conjunctivitis due to bacteria',
        'conjunctivitis due to virus', 'conjunctivitis due to allergy',
        'corneal disorder', 'cornea infection', 'corneal abrasion',
        'pterygium', 'pinguecula', 'endophthalmitis', 'orbital cellulitis',
        'blepharitis', 'chalazion', 'stye', 'eyelid lesion', 'cyst of the eyelid',
        'blepharospasm', 'ectropion', 'entropion', 'trichiasis',
        'eye alignment disorder', 'strabismus', 'amblyopia', 'myopia',
        'hyperopia', 'astigmatism', 'presbyopia', 'aphakia',
        'dry eye of unknown cause', 'floaters', 'foreign body in the eye',
        'subconjunctival hemorrhage', 'optic neuritis'
    ],
    
    # OTORRINOLARINGOLÓGICAS
    'ENT': [
        'acute otitis media', 'chronic otitis media', 'otitis externa (swimmer\'s ear)',
        'mastoiditis', 'cholesteatoma', 'conductive hearing loss',
        'sensorineural hearing loss', 'presbyacusis', 'tinnitus of unknown cause',
        'meniere disease', 'labyrinthitis', 'benign paroxysmal positional vertical (bppv)',
        'eustachian tube dysfunction (ear disorder)', 'ear wax impaction',
        'foreign body in the ear', 'ear drum damage', 'acute sinusitis',
        'chronic sinusitis', 'nasal polyp', 'deviated nasal septum',
        'nose disorder', 'foreign body in the nose', 'abscess of nose',
        'pharyngitis', 'tonsillitis', 'tonsillar hypertrophy',
        'peritonsillar abscess', 'abscess of the pharynx', 'laryngitis',
        'tracheitis', 'croup', 'foreign body in the throat',
        'salivary gland disorder', 'sialoadenitis', 'parotitis',
        'salivary gland stone', 'oral mucosal lesion', 'aphthous ulcer',
        'oral leukoplakia', 'oral thrush (yeast infection)', 'gingivitis',
        'gum disease', 'periodontitis', 'dental caries', 'broken tooth',
        'tooth disorder', 'tooth abscess', 'temporomandibular joint disorder',
        'jaw disorder'
    ],
    
    # HEMATOLÓGICAS/ONCOLÓGICAS
    'Hematological_Oncological': [
        'anemia', 'iron deficiency anemia', 'vitamin b12 deficiency anemia',
        'folate deficiency anemia', 'anemia of chronic disease',
        'anemia due to chronic kidney disease', 'anemia due to malignancy',
        'hemolytic anemia', 'sickle cell anemia', 'sickle cell crisis',
        'thalassemia', 'spherocytosis', 'aplastic anemia', 'myelodysplastic syndrome',
        'polycythemia vera', 'thrombocytopenia', 'primary thrombocythemia',
        'thrombotic thrombocytopenic purpura', 'immune thrombocytopenic purpura',
        'coagulation (bleeding) disorder', 'hemophilia', 'von willebrand disease',
        'disseminated intravascular coagulation', 'deep vein thrombosis (dvt)',
        'thrombophlebitis', 'pulmonary embolism', 'leukemia',
        'acute lymphoblastic leukemia', 'acute myeloid leukemia',
        'chronic lymphocytic leukemia', 'chronic myeloid leukemia',
        'lymphoma', 'hodgkin lymphoma', 'non-hodgkin lymphoma',
        'multiple myeloma', 'myeloproliferative disorder', 'white blood cell disease',
        'lymphadenitis', 'lymphedema', 'splenomegaly', 'hypersplenism',
        'metastatic cancer', 'carcinoid syndrome'
    ],
    
    # REUMATOLÓGICAS/IMUNOLÓGICAS
    'Rheumatological_Immunological': [
        'rheumatoid arthritis', 'systemic lupus erythematosis (sle)',
        'scleroderma', 'polymyositis', 'dermatomyositis', 'vasculitis',
        'polyarteritis nodosa', 'wegener granulomatosis', 'temporal arteritis',
        'giant cell arteritis', 'polymyalgia rheumatica', 'ankylosing spondylitis',
        'reactive arthritis', 'psoriatic arthritis', 'sjogren syndrome',
        'mixed connective tissue disease', 'connective tissue disorder',
        'sarcoidosis', 'amyloidosis', 'cryoglobulinemia', 'raynaud disease',
        'chronic rheumatic fever', 'rheumatic fever', 'allergy',
        'seasonal allergies (hay fever)', 'food allergy', 'allergy to animals',
        'drug allergy', 'allergic reaction', 'anaphylaxis',
        'primary immunodeficiency', 'common variable immunodeficiency',
        'selective iga deficiency', 'hiv', 'aids'
    ],
    
    # OUTRAS/NÃO CLASSIFICADAS
    'Other': [
        'open wound of the neck', 'open wound of the back', 'open wound of the mouth',
        'open wound of the shoulder', 'open wound of the eye', 'open wound of the arm',
        'open wound of the lip', 'open wound of the abdomen', 'open wound of the hand',
        'open wound of the jaw', 'open wound of the foot', 'open wound of the finger',
        'open wound of the face', 'open wound of the ear', 'open wound of the nose',
        'open wound from surgical incision', 'crushing injury', 'birth trauma',
        'hematoma', 'hemarthrosis', 'sprain or strain', 'teething syndrome',
        'neonatal jaundice', 'foreign body in the vagina',
        'foreign body in the gastrointestinal tract', 'foreign body in the eye',
        'foreign body in the ear', 'foreign body in the throat',
        'carbon monoxide poisoning', 'poisoning due to ethylene glycol',
        'poisoning due to analgesics', 'poisoning due to antidepressants',
        'poisoning due to antimicrobial drugs', 'poisoning due to sedatives',
        'poisoning due to anticonvulsants', 'poisoning due to gas',
        'poisoning due to opioids', 'poisoning due to antipsychotics',
        'poisoning due to antihypertensives', 'drug poisoning due to medication',
        'drug reaction', 'heat exhaustion', 'heat stroke', 'hypothermia',
        'frostbite', 'dehydration', 'hypovolemia', 'fluid overload',
        'rhabdomyolysis', 'compartment syndrome', 'fat embolism',
        'air embolism', 'peripheral arterial embolism', 'peripheral arterial disease',
        'thoracic aortic aneurysm', 'abdominal aortic aneurysm',
        'venous insufficiency', 'varicose veins', 'lymphedema',
        'orthostatic hypotension', 'syncope', 'diaper rash',
        'benign vaginal discharge (leukorrhea)', 'vaginal cyst',
        'hydatidiform mole', 'mittelschmerz', 'mastectomy',
        'decubitus ulcer', 'mucositis', 'omphalitis',
        'stenosis of the tear duct', 'thoracic outlet syndrome',
        'tietze syndrome', 'acanthosis nigricans',
        'atrophy of the corpus cavernosum', 'vacterl syndrome',
        'down syndrome', 'edward syndrome', 'fetal alcohol syndrome',
        'congenital malformation syndrome', 'congenital heart defect'
    ]
}

def categorize_disease(disease_name):
    """Categoriza uma doença baseada no dicionário"""
    disease_lower = disease_name.lower().strip()
    for category, diseases in disease_categories.items():
        if disease_lower in [d.lower() for d in diseases]:
            return category
    return 'Other'  # Categoria padrão para doenças não mapeadas

# ========== PASSO 2: CARREGAR E PROCESSAR DATASET ==========
print("Carregando dataset...")
df = pd.read_csv("Final_Augmented_dataset_Diseases_and_Symptoms.csv")

# Remover doenças raras
print("Filtrando doenças...")
disease_counts = df['diseases'].value_counts()
valid_diseases = disease_counts[disease_counts > 1].index
df = df[df['diseases'].isin(valid_diseases)]

# Adicionar coluna de categoria
print("Categorizando doenças...")
df['category'] = df['diseases'].apply(categorize_disease)

# Verificar distribuição de categorias
print("\nDistribuição de Categorias:")
print(df['category'].value_counts())

# ========== PASSO 3: PREPARAR DADOS PARA TREINAMENTO ==========
print("\nPreparando dados para treinamento...")

# Separar features (sintomas) e target (categoria)
X = df.drop(['diseases', 'category'], axis=1)
y = df['category']

# Codificar labels
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# Split treino/teste
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)

print(f"Shape do treino: {X_train.shape}")
print(f"Shape do teste: {X_test.shape}")
print(f"Número de categorias: {len(le.classes_)}")

# ========== PASSO 4: TREINAR MODELO ==========
print("\nTreinando Random Forest Classifier...")
rf_model = RandomForestClassifier(
    n_estimators=200,
    max_depth=30,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1,
    class_weight='balanced'
)

rf_model.fit(X_train, y_train)

# ========== PASSO 5: AVALIAR MODELO ==========
print("\nAvaliando modelo...")
y_pred = rf_model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"\nAcurácia: {accuracy:.4f}")
print("\nRelatório de Classificação:")
print(classification_report(y_test, y_pred, target_names=le.classes_))

# ========== PASSO 6: SALVAR MODELO E METADADOS ==========
print("\nSalvando modelo e metadados...")

# Salvar modelo
with open('disease_classifier_model.pkl', 'wb') as f:
    pickle.dump(rf_model, f)

# Salvar encoder
with open('label_encoder.pkl', 'wb') as f:
    pickle.dump(le, f)

# Salvar lista de sintomas (colunas)
symptom_columns = X.columns.tolist()
with open('symptom_columns.pkl', 'wb') as f:
    pickle.dump(symptom_columns, f)

# Salvar categorias de doenças para referência
with open('disease_categories.json', 'w') as f:
    json.dump(disease_categories, f, indent=2)

print("\nModelo salvo com sucesso!")

# ========== PASSO 7: FUNÇÃO DE PREDIÇÃO COM JSON ==========
def predict_from_json(symptoms_json, model, encoder, columns, top_k=5):
    """
    Faz predição a partir de um JSON de sintomas
    
    Args:
        symptoms_json: dict ou string JSON com sintomas (ex: {"cough": 1, "fever": 1})
        model: modelo treinado
        encoder: LabelEncoder
        columns: lista de colunas (sintomas) do dataset
        top_k: número de categorias a retornar
    
    Returns:
        dict com top_k categorias e suas probabilidades
    """
    # Se for string, converter para dict
    if isinstance(symptoms_json, str):
        symptoms_json = json.loads(symptoms_json)
    
    # Criar vetor de features (todos zeros por padrão)
    features = pd.DataFrame(0, index=[0], columns=columns)
    
    # Preencher com os sintomas do JSON
    for symptom, value in symptoms_json.items():
        if symptom in columns:
            features[symptom] = value
    
    # Fazer predição de probabilidades
    probas = model.predict_proba(features)[0]
    
    # Pegar top_k categorias
    top_indices = probas.argsort()[-top_k:][::-1]
    
    results = []
    for idx in top_indices:
        results.append({
            'category': encoder.classes_[idx],
            'probability': float(probas[idx]),
            'percentage': f"{probas[idx]*100:.2f}%"
        })
    
    return {
        'top_predictions': results,
        'input_symptoms': symptoms_json
    }

# ========== PASSO 8: EXEMPLO DE USO ==========
print("\n" + "="*60)
print("EXEMPLO DE USO DO SISTEMA")
print("="*60)

# Exemplo 1: Sintomas respiratórios
example_json_1 = {
    "cough": 1,
    "shortness of breath": 1,
    "fever": 1,
    "chest tightness": 1
}

print("\nExemplo 1 - Sintomas Respiratórios:")
print(f"Input: {example_json_1}")
result_1 = predict_from_json(example_json_1, rf_model, le, symptom_columns)
print("\nTop 5 Categorias Preditas:")
for pred in result_1['top_predictions']:
    print(f"  {pred['category']}: {pred['percentage']}")

# Exemplo 2: Sintomas cardíacos
example_json_2 = {
    "sharp chest pain": 1,
    "palpitations": 1,
    "shortness of breath": 1,
    "dizziness": 1
}

print("\n" + "-"*60)
print("\nExemplo 2 - Sintomas Cardíacos:")
print(f"Input: {example_json_2}")
result_2 = predict_from_json(example_json_2, rf_model, le, symptom_columns)
print("\nTop 5 Categorias Preditas:")
for pred in result_2['top_predictions']:
    print(f"  {pred['category']}: {pred['percentage']}")

# Exemplo 3: Sintomas gastrointestinais
example_json_3 = {
    "sharp abdominal pain": 1,
    "nausea": 1,
    "vomiting": 1,
    "diarrhea": 1
}

print("\n" + "-"*60)
print("\nExemplo 3 - Sintomas Gastrointestinais:")
print(f"Input: {example_json_3}")
result_3 = predict_from_json(example_json_3, rf_model, le, symptom_columns)
print("\nTop 5 Categorias Preditas:")
for pred in result_3['top_predictions']:
    print(f"  {pred['category']}: {pred['percentage']}")

print("\n" + "="*60)
print("INSTRUÇÕES PARA USO:")
print("="*60)
print("""
1. Carregue o modelo salvo:
   with open('disease_classifier_model.pkl', 'rb') as f:
       model = pickle.load(f)
   with open('label_encoder.pkl', 'rb') as f:
       encoder = pickle.load(f)
   with open('symptom_columns.pkl', 'rb') as f:
       columns = pickle.load(f)

2. Crie um JSON com sintomas (1 = presente, sintomas ausentes = 0 por padrão):
   symptoms = {
       "cough": 1,
       "fever": 1,
       "headache": 1
   }

3. Faça a predição:
   result = predict_from_json(symptoms, model, encoder, columns, top_k=5)
   
4. Acesse os resultados:
   for pred in result['top_predictions']:
       print(f"{pred['category']}: {pred['percentage']}")
""")

