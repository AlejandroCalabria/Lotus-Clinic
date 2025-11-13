CREATE DATABASE clinica_med;
USE clinica_med;

-- Tabelas (exatamente como estavam)
CREATE TABLE cargo(
    cod_cargo VARCHAR(16) PRIMARY KEY,
    cargo_descricao VARCHAR(256) NOT NULL,
    cargo_nome VARCHAR(32) NOT NULL
);

CREATE TABLE usuario(
    cod_usuario VARCHAR(16) PRIMARY KEY,
    CPF VARCHAR(11) UNIQUE NOT NULL,
    Nome_user VARCHAR(50) NOT NULL,
    telefone VARCHAR(11),
    email VARCHAR(256) UNIQUE,
    sexo ENUM('M','F','NB') NOT NULL,
    data_nasc DATE NOT NULL,
    senha VARCHAR(64) NOT NULL,
    foto VARCHAR(255) DEFAULT NULL,  -- ← JÁ INCLUÍDO
    cod_cargo VARCHAR(16) NOT NULL,
    FOREIGN KEY (cod_cargo) REFERENCES cargo(cod_cargo)
);

CREATE TABLE medico(
    cod_medico VARCHAR(5) PRIMARY KEY,
    CRM VARCHAR(6) UNIQUE NOT NULL,
    especialidade VARCHAR(100) DEFAULT 'Clínico Geral',  -- ← JÁ INCLUÍDO
    anos_experiencia INT DEFAULT 0,  -- ← JÁ INCLUÍDO
    atividade BOOL DEFAULT TRUE,
    cod_usuario VARCHAR(16) NOT NULL,
    FOREIGN KEY (cod_usuario) REFERENCES usuario (cod_usuario)
);

CREATE TABLE convenio(
    nome_convenio VARCHAR(20) NOT NULL,
    tipo_convenio SET('P','E') NOT NULL,
    validade_convenio DATE NOT NULL,
    cod_convenio VARCHAR(5) PRIMARY KEY
);

-- ✅ CONSULTA COM ENUM CORRETO DESDE O INÍCIO
CREATE TABLE consulta(
    cod_consulta VARCHAR(10) PRIMARY KEY,
    data_consulta DATE NOT NULL,
    hora_consulta TIME NOT NULL,
    tipo_atendimento ENUM('Rotina','Retorno','Urgência') NOT NULL,
    status_consulta ENUM(
        'Aguardando Triagem',
        'Aguardando Consulta', 
        'Confirmada',
        'Aguardando Exame',
        'Tratamento em Andamento',
        'Retorno Agendado',
        'Concluída',
        'Cancelada'
    ) NOT NULL DEFAULT 'Aguardando Triagem',  -- ← JÁ CORRETO
    cod_medico VARCHAR(5) NOT NULL,
    cod_usuario VARCHAR(16) NOT NULL,
    cod_convenio VARCHAR(5) NOT NULL,
    local_consulta VARCHAR(16),
    UNIQUE(hora_consulta, local_consulta),
    FOREIGN KEY(cod_usuario) REFERENCES usuario(cod_usuario),
    FOREIGN KEY (cod_medico) REFERENCES medico(cod_medico),
    FOREIGN KEY (cod_convenio) REFERENCES convenio(cod_convenio)
);

-- ✅ TRIAGEM JÁ CRIADA
CREATE TABLE triagem (
    cod_triagem VARCHAR(10) PRIMARY KEY,
    cod_consulta VARCHAR(10) NOT NULL,
    sintomas_relatados TEXT NOT NULL,
    categoria_ia VARCHAR(50),
    probabilidade_ia DECIMAL(5,2),
    nivel_urgencia ENUM('Rotina','Urgência','Emergência') NOT NULL,
    observacoes_triagem TEXT,
    data_triagem DATETIME DEFAULT CURRENT_TIMESTAMP,
    cod_atendente VARCHAR(16) NOT NULL,
    FOREIGN KEY (cod_consulta) REFERENCES consulta(cod_consulta),
    FOREIGN KEY (cod_atendente) REFERENCES usuario(cod_usuario)
);

CREATE TABLE medicamento (
    cod_medicamento VARCHAR(5) PRIMARY KEY,
    nome_medicamento VARCHAR(30) UNIQUE NOT NULL,
    tipo_medicamento VARCHAR(30) NOT NULL,
    cod_consulta VARCHAR(10) NOT NULL,
    FOREIGN KEY (cod_consulta) REFERENCES consulta(cod_consulta)
);

CREATE TABLE prescricao(
    cod_prescr VARCHAR(10) PRIMARY KEY,
    modo_uso VARCHAR(256) NOT NULL,
    dosagem NUMERIC NOT NULL CHECK(dosagem > 0),
    cod_consulta VARCHAR(10) NOT NULL,
    cod_medicamento VARCHAR(5) NOT NULL,
    FOREIGN KEY (cod_consulta) REFERENCES consulta(cod_consulta),
    FOREIGN KEY (cod_medicamento) REFERENCES medicamento(cod_medicamento)
);

CREATE TABLE grade_horaria(
    cod_grade VARCHAR(10) PRIMARY KEY,
    datas_atendimento DATE NOT NULL,
    horario_disponivel VARCHAR(5) NOT NULL,
    tipo_consulta VARCHAR(50) NOT NULL,
    status_disponivel ENUM('Disponível','Não Disponível') DEFAULT 'Disponível',
    cod_usuario VARCHAR(16) NOT NULL,
    FOREIGN KEY (cod_usuario) REFERENCES usuario(cod_usuario)
);

-- ✅ HISTORICO_MEDICO COM NOVOS CAMPOS
CREATE TABLE historico_medico(
    cod_historico_medico VARCHAR(15) PRIMARY KEY,
    profissao VARCHAR(50),
    peso NUMERIC CHECK(peso > 0),
    altura NUMERIC CHECK(altura > 0),
    tipo_sanguineo ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'),
    medicamentos VARCHAR(256),
    cigarro_uso BOOL DEFAULT FALSE,
    alcool_uso BOOL DEFAULT FALSE,
    exercicio_fisico BOOL DEFAULT FALSE,
    diagnosticos TEXT,  -- ← JÁ INCLUÍDO
    ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,  -- ← JÁ INCLUÍDO
    cod_usuario VARCHAR(16) NOT NULL,
    FOREIGN KEY (cod_usuario) REFERENCES usuario(cod_usuario)
);

CREATE TABLE desconto(
    valor_desconto NUMERIC(11,2) NOT NULL CHECK(valor_desconto >= 0),
    proced_relacionado VARCHAR(30) NOT NULL,
    cod_desconto VARCHAR(5) PRIMARY KEY,
    cod_convenio VARCHAR(5) NOT NULL,
    FOREIGN KEY (cod_convenio) REFERENCES convenio(cod_convenio)
);

CREATE TABLE procedimentos(
    cod_procedimento VARCHAR(15) PRIMARY KEY,
    tipo_procedimento VARCHAR(50) NOT NULL,
    instru_procedimento VARCHAR(50),
    requer_exame BOOL DEFAULT FALSE,
    desc_requisitos VARCHAR(50),
    cod_usuario VARCHAR(16) NOT NULL,
    cod_medico VARCHAR(5) NOT NULL,
    cod_convenio VARCHAR(5) NOT NULL,
    FOREIGN KEY (cod_convenio) REFERENCES convenio(cod_convenio),
    FOREIGN KEY (cod_usuario) REFERENCES usuario(cod_usuario),
    FOREIGN KEY (cod_medico) REFERENCES medico(cod_medico)
);

CREATE TABLE exec_procedimentos(
    data_proced DATE NOT NULL,
    local_proced VARCHAR(30) NOT NULL,
    hora_procedimento TIME NOT NULL,
    status_proced ENUM('Concluído','Aguardando', 'Cancelado') NOT NULL,
    cod_procedimento VARCHAR(15) NOT NULL,
    UNIQUE(local_proced, hora_procedimento),
    cod_medico VARCHAR(5) NOT NULL,
    FOREIGN KEY (cod_procedimento) REFERENCES procedimentos(cod_procedimento),
    FOREIGN KEY (cod_medico) REFERENCES medico(cod_medico)
);

CREATE TABLE visualiza_procedimento(
    data_proced DATE NOT NULL,
    local_proced VARCHAR(30) NOT NULL,
    status_proced ENUM('Concluído','Aguardando', 'Cancelado') DEFAULT 'Aguardando',
    cod_procedimento VARCHAR(15) NOT NULL,
    cod_usuario VARCHAR(16) NOT NULL,
    FOREIGN KEY (cod_procedimento) REFERENCES procedimentos(cod_procedimento),
    FOREIGN KEY (cod_usuario) REFERENCES usuario(cod_usuario)
);

-- ===== INSERTS (usando os novos status) =====

INSERT INTO cargo (cod_cargo, cargo_descricao, cargo_nome) VALUES
('C001', 'Profissional responsável pelo atendimento médico aos pacientes', 'Médico'),
('C002', 'Usuário que busca atendimento clínico na instituição', 'Paciente'),
('C003', 'Responsável por agendamentos e recepção de pacientes', 'Atendente'),
('C004', 'Profissional responsável pela manutenção e desenvolvimento do sistema da clínica', 'Desenvolvedor'),
('C005', 'Desenvolvedor backend com foco em banco de dados', 'Desenvolvedor');

INSERT INTO usuario (cod_usuario, CPF, Nome_user, telefone, email, sexo, data_nasc, senha, cod_cargo) VALUES
('U001', '12345678901', 'Ana Souza', '11987654321', 'ana@email.com', 'F', '1985-04-20', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'C001'),
('U002', '98765432100', 'Carlos Rocha', '21987654321', 'carlos@email.com', 'M', '2002-05-10', 'senha456', 'C002'),
('U003', '45678912301', 'Mariana Costa', '31987654321', 'mariana@email.com', 'F', '1992-07-15', 'senha789', 'C003'),
('U004', '32165498702', 'João Almeida', '41987654321', 'joao@email.com', 'M', '1987-12-30', 'senha321', 'C002'),
('U005', '65498732103', 'Paula Martins', '51987654321', 'paula@email.com', 'F', '1988-11-12', 'senha654', 'C002'),
('U006', '78912345604', 'Lucas Pereira', '61987654321', 'lucas@email.com', 'M', '1991-03-22', 'senha987', 'C005'),
('U007', '85296374105', 'Juliana Rocha', '71987654321', 'juliana@email.com', 'F', '1989-09-14', 'senha321', 'C004'),
('U008', '96325874106', 'Rafael Souza', '81987654321', 'rafael@email.com', 'M', '1993-06-28', 'senha654', 'C003'),
('U009', '74185296307', 'Sofia Oliveira', '91987654321', 'sofia@email.com', 'F', '1994-01-25', 'senha987', 'C002'),
('U010', '85274196308', 'Felipe Santos', '22987654321', 'felipe@email.com', 'M', '1986-02-18', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'C001'),
('U011', '15975345609', 'Marcos Rocha', '33987654321', 'marcos@email.com', 'M', '1995-08-12', 'senha456', 'C002'),
('U012', '74125836910', 'Larissa Dias', '44987654321', 'larissa@email.com', 'F', '1991-10-03', 'senha789', 'C003'),
('U013', '96314725811', 'Vinícius Lima', '55987654321', 'vinicius@email.com', 'M', '1990-07-19', 'senha321', 'C004'),
('U014', '25896374112', 'Fernanda Martins', '66987654321', 'fernanda@email.com', 'F', '1987-12-11', 'senha654', 'C001'),
('U015', '14725896313', 'Ricardo Alves', '77987654321', 'ricardo@email.com', 'M', '1992-05-15', 'senha987', 'C002'),
('U022', '11335678601', 'Ana Souza Ramos Vieira', '11987654321', 'ana.ramos@email.com', 'NB', '1985-04-20', 'senha123', 'C002');

INSERT INTO medico (cod_medico, CRM, especialidade, anos_experiencia, atividade, cod_usuario) VALUES
('M001', '123456', 'Cardiologista', 12, TRUE, 'U001'),
('M002', '34567', 'Pediatria', 8, TRUE, 'U010'),
('M003', '345678', 'Ortopedia', 15, TRUE, 'U014');

INSERT INTO convenio (nome_convenio, tipo_convenio, validade_convenio, cod_convenio) VALUES
('Unimed', 'P', '2026-12-31', 'CV001'),
('Bradesco', 'P', '2026-11-30', 'CV002'),
('Amil', 'P', '2026-10-15', 'CV003');

-- ✅ INSERTS DE CONSULTA COM STATUS NOVOS
INSERT INTO consulta (cod_consulta, data_consulta, hora_consulta, tipo_atendimento, status_consulta, cod_usuario, cod_medico, cod_convenio, local_consulta) VALUES
('C001', '2025-01-10', '14:00', 'Retorno', 'Confirmada', 'U022', 'M001', 'CV001', 'sala 131'),
('C002', '2025-06-10', '14:00', 'Retorno', 'Confirmada', 'U002', 'M001', 'CV001', 'sala 132'),
('C003', '2025-06-11', '14:00', 'Rotina', 'Cancelada', 'U004', 'M002', 'CV002', 'sala 133'),
('C007', '2025-06-15', '14:40', 'Rotina', 'Aguardando Consulta', 'U006', 'M003', 'CV003', 'sala 132');

INSERT INTO triagem (cod_triagem, cod_consulta, sintomas_relatados, categoria_ia, probabilidade_ia, nivel_urgencia, observacoes_triagem, cod_atendente) VALUES
('T001', 'C001', 'febre, tosse, dor de cabeça', 'Respiratória', 85.50, 'Rotina', 'Paciente com sintomas gripais leves', 'U003'),
('T002', 'C002', 'dor no peito, palpitações', 'Cardiovascular', 92.30, 'Urgência', 'Encaminhado para cardiologista', 'U003');

-- Índices
CREATE INDEX idx_consulta_medico_data ON consulta(cod_medico, data_consulta);
CREATE INDEX idx_usuario_email ON usuario(email);

-- Verificar
SELECT * FROM consulta;
SELECT * FROM triagem;
DESCRIBE consulta;
DESCRIBE usuario;
DESCRIBE medico;
DESCRIBE historico_medico;

UPDATE usuario SET senha = '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92' WHERE email = 'carlos@email.com';  -- senha456
UPDATE usuario SET senha = '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8' WHERE email = 'mariana@email.com';  -- senha789
UPDATE usuario SET senha = 'e1608f75c5d7813f3d4031cb30bfb786507d98137538ff8e128a6ff74e84e643' WHERE email = 'joao@email.com';     -- senha321
UPDATE usuario SET senha = '8d6c8b0f3c2e4d5a9b7f1e3c6d8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a' WHERE email = 'paula@email.com';    -- senha654
UPDATE usuario SET senha = '3c9909afec25354d551dae21590bb26e38d53f2173b8d3dc3eee4c047e7ab1c1' WHERE email = 'lucas@email.com';    -- senha987
UPDATE usuario SET senha = 'e1608f75c5d7813f3d4031cb30bfb786507d98137538ff8e128a6ff74e84e643' WHERE email = 'juliana@email.com';  -- senha321
UPDATE usuario SET senha = '8d6c8b0f3c2e4d5a9b7f1e3c6d8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a' WHERE email = 'rafael@email.com';   -- senha654
UPDATE usuario SET senha = '3c9909afec25354d551dae21590bb26e38d53f2173b8d3dc3eee4c047e7ab1c1' WHERE email = 'sofia@email.com';    -- senha987
UPDATE usuario SET senha = '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92' WHERE email = 'marcos@email.com';   -- senha456
UPDATE usuario SET senha = '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8' WHERE email = 'larissa@email.com';  -- senha789
UPDATE usuario SET senha = 'e1608f75c5d7813f3d4031cb30bfb786507d98137538ff8e128a6ff74e84e643' WHERE email = 'vinicius@email.com'; -- senha321
UPDATE usuario SET senha = '3c9909afec25354d551dae21590bb26e38d53f2173b8d3dc3eee4c047e7ab1c1' WHERE email = 'ricardo@email.com';  -- senha987
UPDATE usuario SET senha = '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92' WHERE email = 'ana.ramos@email.com'; -- senha123

SELECT email, LEFT(senha, 20) as senha_hash FROM usuario WHERE cod_cargo = 'C002';

SELECT 
    email, 
    senha,
    CHAR_LENGTH(senha) as tamanho_hash
FROM usuario 
WHERE email IN ('ana@email.com', 'carlos@email.com');

UPDATE usuario 
SET senha = '6b08d780140e292a4af8ba3f2333fc1357091442d7e807c6cad92e8dcd0240b7'
WHERE email = 'carlos@email.com';

-- Verificar
SELECT email, senha FROM usuario WHERE email = 'carlos@email.com';
ALTER TABLE consulta ADD COLUMN sintomas_triagem TEXT AFTER local_consulta;
-- Adicionar mais médicos com especialidades variadas
INSERT INTO usuario (cod_usuario, CPF, Nome_user, telefone, email, sexo, data_nasc, senha, cod_cargo) VALUES
('U023', '11122233344', 'Maria Silva', '11999887766', 'maria.silva@email.com', 'F', '1980-05-15', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'C001'),
('U024', '22233344455', 'João Santos', '11988776655', 'joao.santos@email.com', 'M', '1975-08-20', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'C001'),
('U025', '33344455566', 'Carla Oliveira', '11977665544', 'carla.oliveira@email.com', 'F', '1982-03-10', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'C001');

INSERT INTO medico (cod_medico, CRM, especialidade, anos_experiencia, atividade, cod_usuario) VALUES
('M016', '111222', 'Ginecologia', 10, TRUE, 'U023'),
('M017', '222333', 'Neurologia', 15, TRUE, 'U024'),
('M018', '333444', 'Dermatologia', 8, TRUE, 'U025');

-- Atualizar médicos existentes com especialidades diferentes
UPDATE medico SET especialidade = 'Psiquiatria', anos_experiencia = 7 WHERE cod_medico = 'M004';
UPDATE medico SET especialidade = 'Clínico Geral', anos_experiencia = 5 WHERE cod_medico = 'M005';
ALTER TABLE consulta MODIFY COLUMN cod_medico VARCHAR(5) NULL;

-- ADICIONAR APÓS A TABELA convenio
CREATE TABLE unidade (
    cod_unidade VARCHAR(5) PRIMARY KEY,
    nome_unidade VARCHAR(100) NOT NULL,
    endereco VARCHAR(255) NOT NULL,
    telefone VARCHAR(15),
    ativo BOOL DEFAULT TRUE
);

-- INSERIR UNIDADES
INSERT INTO unidade (cod_unidade, nome_unidade, endereco, telefone, ativo) VALUES
('UN001', 'Unidade Centro', 'Av. Afonso Pena, 1234 - Centro, Uberlândia/MG', '(34) 3234-5678', TRUE),
('UN002', 'Unidade Jardins', 'Rua das Flores, 567 - Jardim Karaíba, Uberlândia/MG', '(34) 3234-5679', TRUE),
('UN003', 'Unidade Santa Mônica', 'Av. Rondon Pacheco, 890 - Santa Mônica, Uberlândia/MG', '(34) 3234-5680', TRUE);

-- ADICIONAR APÓS A TABELA unidade
CREATE TABLE sala (
    cod_sala VARCHAR(10) PRIMARY KEY,
    numero_sala VARCHAR(10) NOT NULL,
    tipo_sala ENUM('Triagem', 'Consultório', 'Exame', 'Procedimento') NOT NULL,
    cod_unidade VARCHAR(5) NOT NULL,
    ativo BOOL DEFAULT TRUE,
    FOREIGN KEY (cod_unidade) REFERENCES unidade(cod_unidade)
);

-- INSERIR SALAS
INSERT INTO sala (cod_sala, numero_sala, tipo_sala, cod_unidade, ativo) VALUES
-- Unidade Centro
('S001', '101', 'Triagem', 'UN001', TRUE),
('S002', '102', 'Triagem', 'UN001', TRUE),
('S003', '103', 'Consultório', 'UN001', TRUE),
('S004', '104', 'Consultório', 'UN001', TRUE),
('S005', '105', 'Exame', 'UN001', TRUE),
-- Unidade Jardins
('S006', '201', 'Triagem', 'UN002', TRUE),
('S007', '202', 'Consultório', 'UN002', TRUE),
('S008', '203', 'Consultório', 'UN002', TRUE),
-- Unidade Santa Mônica
('S009', '301', 'Triagem', 'UN003', TRUE),
('S010', '302', 'Consultório', 'UN003', TRUE);

-- ADICIONAR DEPOIS DOS CARGOS EXISTENTES
INSERT INTO cargo (cod_cargo, cargo_descricao, cargo_nome) VALUES
('C006', 'Profissional de enfermagem responsável pela triagem de pacientes', 'Enfermeiro(a)');

-- ADICIONAR APÓS A TABELA medico
CREATE TABLE enfermeiro (
    cod_enfermeiro VARCHAR(5) PRIMARY KEY,
    COREN VARCHAR(10) UNIQUE NOT NULL,
    especialidade VARCHAR(100) DEFAULT 'Triagem',
    anos_experiencia INT DEFAULT 0,
    atividade BOOL DEFAULT TRUE,
    cod_usuario VARCHAR(16) NOT NULL,
    FOREIGN KEY (cod_usuario) REFERENCES usuario(cod_usuario)
);
-- ADICIONAR APÓS OS USUÁRIOS EXISTENTES
INSERT INTO usuario (cod_usuario, CPF, Nome_user, telefone, email, sexo, data_nasc, senha, cod_cargo) VALUES
('U026', '44455566677', 'Sandra Lima', '11966554433', 'sandra.enfermeira@email.com', 'F', '1988-06-25', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'C006'),
('U027', '55566677788', 'Roberto Costa', '11955443322', 'roberto.enfermeiro@email.com', 'M', '1985-11-10', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'C006');

insert into usuario(cod_usuario, cpf, nome_user, telefone, email, sexo, data_nasc, senha, cod_cargo) values
('U060', '44455566678', 'Alezinho', '11966554434', 'alezinho@email.com', 'M', '1988-06-25', 'b578dc5fcbfabbc7e96400601d0858c951f04929faef033bbbc117ab935c6ae9', 'C005');

INSERT INTO enfermeiro (cod_enfermeiro, COREN, especialidade, anos_experiencia, atividade, cod_usuario) VALUES
('E001', '123456-MG', 'Triagem', 8, TRUE, 'U026'),
('E002', '234567-MG', 'Triagem', 12, TRUE, 'U027');

-- ADICIONAR CAMPOS NA TABELA consulta
ALTER TABLE consulta 
ADD COLUMN cod_unidade VARCHAR(5) AFTER local_consulta,
ADD COLUMN cod_sala VARCHAR(10) AFTER cod_unidade,
ADD COLUMN sintomas_descritos TEXT AFTER sintomas_triagem,
ADD COLUMN horario_preferencial_paciente TIME AFTER hora_consulta,
ADD FOREIGN KEY (cod_unidade) REFERENCES unidade(cod_unidade),
ADD FOREIGN KEY (cod_sala) REFERENCES sala(cod_sala);

-- ALTERAR CAMPOS NA TABELA triagem
ALTER TABLE triagem 
MODIFY COLUMN cod_atendente VARCHAR(16) NULL,
ADD COLUMN cod_enfermeiro VARCHAR(5) AFTER cod_atendente,
ADD COLUMN relatorio_ia_json TEXT AFTER probabilidade_ia,
ADD COLUMN medico_sugerido VARCHAR(5) AFTER relatorio_ia_json,
ADD FOREIGN KEY (cod_enfermeiro) REFERENCES enfermeiro(cod_enfermeiro),
ADD FOREIGN KEY (medico_sugerido) REFERENCES medico(cod_medico);

-- NOVA TABELA para notificações
CREATE TABLE notificacao (
    cod_notificacao VARCHAR(15) PRIMARY KEY,
    tipo_notificacao ENUM('Triagem Agendada', 'Consulta Marcada', 'Resultado Disponível', 'Geral') NOT NULL,
    titulo VARCHAR(100) NOT NULL,
    mensagem TEXT NOT NULL,
    lida BOOL DEFAULT FALSE,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    cod_usuario_destino VARCHAR(16) NOT NULL,
    cod_consulta VARCHAR(10),
    FOREIGN KEY (cod_usuario_destino) REFERENCES usuario(cod_usuario),
    FOREIGN KEY (cod_consulta) REFERENCES consulta(cod_consulta)
);

-- ALTERAR especialidades do médico para incluir todas as categorias
ALTER TABLE medico MODIFY COLUMN especialidade ENUM(
    'Clínico Geral',
    'Cardiologista',
    'Pediatria',
    'Ortopedia',
    'Ginecologia',
    'Dermatologia',
    'Neurologia',
    'Psiquiatria',
    'Respiratório',
    'Gastrointestinal',
    'Endocrinologia',
    'Urologia',
    'Oftalmologia',
    'Otorrinolaringologia',
    'Hematologia',
    'Oncologia',
    'Infectologia'
) DEFAULT 'Clínico Geral';

ALTER TABLE consulta MODIFY COLUMN hora_consulta TIME NULL;

UPDATE usuario SET senha = 'b578dc5fcbfabbc7e96400601d0858c951f04929faef033bbbc117ab935c6ae9' 
WHERE email = 'mariana@email.com';

SELECT u.email, u.Nome_user, u.cod_cargo, c.cargo_nome
FROM usuario u
JOIN cargo c ON u.cod_cargo = c.cod_cargo
WHERE u.email = 'mariana@email.com';

-- Alterar coluna foto para TEXT (suporta base64 grande)
ALTER TABLE usuario MODIFY COLUMN foto TEXT;