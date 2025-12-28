/**
 * SISTEMA DE MODO ESCURO - CLÍNICA LOTUS
 * VERSÃO OTIMIZADA COM APLICAÇÃO FORÇADA
 */

(function() {
    'use strict';

    // Função para aplicar o tema IMEDIATAMENTE
    function aplicarTema(tema) {
        if (tema === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            document.body.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
            document.body.removeAttribute('data-theme');
        }
        
        // Forçar recálculo de estilos
        document.body.offsetHeight;
    }

    // Função para obter o tema atual
    function obterTemaAtual() {
        return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    }

    // Função para alternar o tema
    function alternarTema() {
        const temaAtual = obterTemaAtual();
        const novoTema = temaAtual === 'dark' ? 'light' : 'dark';
        
        aplicarTema(novoTema);
        localStorage.setItem('lotus-theme', novoTema);
        
        // Log para debug
        console.log('🌙 Tema alterado para:', novoTema);
        
        // Adiciona animação de rotação ao ícone
        const botao = document.getElementById('darkModeToggle');
        if (botao) {
            botao.style.transform = 'rotate(360deg)';
            setTimeout(() => {
                botao.style.transform = 'rotate(0deg)';
            }, 300);
        }
        
        // Dispara evento personalizado
        window.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { theme: novoTema } 
        }));
    }

    // Inicializar o tema ANTES de tudo
    function inicializarTema() {
        const temaSalvo = localStorage.getItem('lotus-theme');
        
        if (temaSalvo) {
            console.log('✅ Tema salvo encontrado:', temaSalvo);
            aplicarTema(temaSalvo);
        } else {
            // Verificar preferência do sistema
            const prefereEscuro = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const temaInicial = prefereEscuro ? 'dark' : 'light';
            console.log('🎨 Aplicando tema do sistema:', temaInicial);
            aplicarTema(temaInicial);
        }
    }

    // Criar botão de toggle
    function criarBotaoToggle() {
        if (document.getElementById('darkModeToggle')) {
            return document.getElementById('darkModeToggle');
        }

        const botao = document.createElement('button');
        botao.id = 'darkModeToggle';
        botao.className = 'dark-mode-toggle';
        botao.title = 'Alternar modo escuro';
        botao.innerHTML = '<i class="bi bi-moon-stars-fill"></i>';
        botao.setAttribute('aria-label', 'Alternar modo escuro');
        
        document.body.appendChild(botao);
        
        console.log('🔘 Botão de modo escuro criado');
        return botao;
    }

    // ⚡ APLICAR TEMA IMEDIATAMENTE - ANTES DO DOM CARREGAR
    inicializarTema();

    // Inicializar quando possível
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        // Garantir que o tema está aplicado
        inicializarTema();
        
        // Criar ou pegar o botão
        const botao = criarBotaoToggle();
        
        // Adicionar evento de clique
        if (botao) {
            botao.addEventListener('click', alternarTema);
            console.log('✅ Evento de clique adicionado ao botão');
        }
        
        // Também adiciona listener ao botão se ele já existir no HTML
        const botaoExistente = document.getElementById('darkModeToggle');
        if (botaoExistente && botaoExistente !== botao) {
            botaoExistente.addEventListener('click', alternarTema);
        }
        
        // Monitora mudanças na preferência do sistema
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('lotus-theme')) {
                aplicarTema(e.matches ? 'dark' : 'light');
            }
        });
        
        // Log do status atual
        const temaAtual = obterTemaAtual();
        console.log('🎨 Sistema de modo escuro inicializado!');
        console.log('📌 Tema atual:', temaAtual);
        console.log('💾 Tema salvo:', localStorage.getItem('lotus-theme'));
    }

    // Exportar API global
    window.lotusTheme = {
        toggle: alternarTema,
        set: aplicarTema,
        get: obterTemaAtual,
        reset: function() {
            localStorage.removeItem('lotus-theme');
            inicializarTema();
            console.log('🔄 Tema resetado');
        },
        debug: function() {
            console.log('🐛 DEBUG - Estado do tema:');
            console.log('  - Tema atual:', obterTemaAtual());
            console.log('  - Tema salvo:', localStorage.getItem('lotus-theme'));
            console.log('  - Preferência do sistema:', 
                window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
            console.log('  - Atributo data-theme:', document.documentElement.getAttribute('data-theme'));
        }
    };

    // Log de inicialização
    console.log('🌙 Dark Mode Script loaded!');
    console.log('💡 Use window.lotusTheme.debug() para depurar');

})();