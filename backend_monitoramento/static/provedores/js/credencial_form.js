/**
 * Mostra/esconde campos de credenciais conforme o provedor selecionado
 * e atualiza os labels com nomes amigaveis.
 */
(function () {
  'use strict';

  var CAMPOS_POR_PROVEDOR = {
    solis:       [{campo: 'campo_1', label: 'API Key'},        {campo: 'campo_2', label: 'App Secret'}],
    hoymiles:    [{campo: 'campo_1', label: 'Usuário / Email'},{campo: 'campo_2', label: 'Senha'}],
    fusionsolar: [{campo: 'campo_1', label: 'Usuário'},        {campo: 'campo_2', label: 'System Code'}],
    solarman:    [{campo: 'campo_1', label: 'App ID'},         {campo: 'campo_2', label: 'App Secret'}, {campo: 'campo_3', label: 'Email'}, {campo: 'campo_4', label: 'Senha'}],
    auxsol:      [{campo: 'campo_1', label: 'Usuário / Email'},{campo: 'campo_2', label: 'Senha'}],
  };

  function atualizarCampos() {
    var select = document.getElementById('id_provedor');
    if (!select) return;

    var provedor = select.value;
    var config = CAMPOS_POR_PROVEDOR[provedor] || [];
    var camposUsados = config.map(function (c) { return c.campo; });

    // Mostrar/esconder campos
    ['campo_1', 'campo_2', 'campo_3', 'campo_4'].forEach(function (nome) {
      var row = document.querySelector('.form-row.field-' + nome) ||
                (function () {
                  var el = document.getElementById('id_' + nome);
                  return el ? el.closest('.form-row, .grp-row, tr') : null;
                })();
      if (!row) return;

      if (camposUsados.indexOf(nome) >= 0) {
        row.style.display = '';
        var cfgItem = config.find(function (c) { return c.campo === nome; });
        var label = row.querySelector('label[for="id_' + nome + '"]');
        if (label && cfgItem) {
          label.textContent = cfgItem.label + ':';
        }
      } else {
        row.style.display = 'none';
        var input = document.getElementById('id_' + nome);
        if (input) input.value = '';
      }
    });
  }

  function init() {
    var select = document.getElementById('id_provedor');
    if (!select) return;

    select.addEventListener('change', atualizarCampos);
    atualizarCampos();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
