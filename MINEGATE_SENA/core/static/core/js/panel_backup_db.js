(function () {
  function useAlert(message, type) {
    if (typeof window.mAlert === "function") {
      return window.mAlert(message, type);
    }
    window.alert(message);
    return Promise.resolve(true);
  }

  function useConfirm(message, options) {
    if (typeof window.mConfirm === "function") {
      return window.mConfirm(message, options || {});
    }
    return Promise.resolve(window.confirm(message));
  }

  function bloquearBoton(boton, textoCargando) {
    if (!boton) return;
    if (!boton.dataset.originalText) {
      boton.dataset.originalText = boton.innerHTML;
    }
    boton.disabled = true;
    boton.innerHTML = '<i class="ri-loader-4-line"></i><span>' + textoCargando + "</span>";
  }

  function crearControlModalPassword() {
    var modal = document.getElementById("backupPasswordModal");
    if (!modal) {
      return {
        solicitar: function () {
          return Promise.resolve(null);
        },
      };
    }

    var titulo = modal.querySelector("[data-password-title]");
    var subtitulo = modal.querySelector("[data-password-subtitle]");
    var icono = document.getElementById("backupPasswordModalIcon");
    var input = document.getElementById("backupPasswordInput");
    var error = document.getElementById("backupPasswordError");
    var btnCerrar = modal.querySelector("[data-password-close]");
    var btnCancelar = modal.querySelector("[data-password-cancel]");
    var btnConfirmar = modal.querySelector("[data-password-confirm]");
    var btnToggle = document.getElementById("backupPasswordToggle");

    var resolverActivo = null;

    function mostrarError(mensaje) {
      if (!error) return;
      error.textContent = mensaje;
      error.classList.add("is-visible");
    }

    function ocultarError() {
      if (!error) return;
      error.classList.remove("is-visible");
    }

    function cerrarModal(resultado) {
      if (resolverActivo) {
        var resolver = resolverActivo;
        resolverActivo = null;
        resolver(resultado);
      }

      modal.classList.remove("is-visible");
      modal.setAttribute("aria-hidden", "true");

      if (input) {
        input.value = "";
        input.type = "password";
      }

      if (btnToggle) {
        btnToggle.innerHTML = '<i class="ri-eye-line"></i>';
      }

      ocultarError();
      document.body.classList.remove("backup-modal-open");
    }

    function abrirModal(config) {
      if (titulo) {
        titulo.textContent = config.title || "Confirmar identidad";
      }
      if (subtitulo) {
        subtitulo.textContent =
          config.subtitle || "Ingresa tu contraseña para validar la accion.";
      }
      if (icono) {
        icono.className = config.iconClass || "ri-shield-keyhole-line";
      }
      if (btnConfirmar) {
        var textoBoton = config.confirmText || "Confirmar";
        btnConfirmar.innerHTML =
          '<i class="ri-check-line"></i><span>' + textoBoton + "</span>";
        btnConfirmar.classList.remove("is-danger", "is-warning", "is-success");
        if (config.variant === "danger") {
          btnConfirmar.classList.add("is-danger");
        } else if (config.variant === "warning") {
          btnConfirmar.classList.add("is-warning");
        } else {
          btnConfirmar.classList.add("is-success");
        }
      }

      if (input) {
        input.value = "";
        input.type = "password";
      }
      if (btnToggle) {
        btnToggle.innerHTML = '<i class="ri-eye-line"></i>';
      }

      ocultarError();
      modal.classList.add("is-visible");
      modal.setAttribute("aria-hidden", "false");
      document.body.classList.add("backup-modal-open");

      window.setTimeout(function () {
        if (input) {
          input.focus();
        }
      }, 40);

      return new Promise(function (resolve) {
        resolverActivo = resolve;
      });
    }

    if (btnCerrar) {
      btnCerrar.addEventListener("click", function () {
        cerrarModal(null);
      });
    }

    if (btnCancelar) {
      btnCancelar.addEventListener("click", function () {
        cerrarModal(null);
      });
    }

    if (modal) {
      modal.addEventListener("click", function (event) {
        if (event.target === modal) {
          cerrarModal(null);
        }
      });
    }

    if (btnToggle && input) {
      btnToggle.addEventListener("click", function () {
        var esPassword = input.type === "password";
        input.type = esPassword ? "text" : "password";
        btnToggle.innerHTML = esPassword
          ? '<i class="ri-eye-off-line"></i>'
          : '<i class="ri-eye-line"></i>';
      });
    }

    if (btnConfirmar) {
      btnConfirmar.addEventListener("click", function () {
        var valor = input ? String(input.value || "").trim() : "";
        if (!valor) {
          mostrarError("Debes ingresar la contraseña para continuar.");
          return;
        }
        cerrarModal(valor);
      });
    }

    if (input) {
      input.addEventListener("input", function () {
        ocultarError();
      });
      input.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
          if (btnConfirmar) {
            btnConfirmar.click();
          }
        }
      });
    }

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && modal.classList.contains("is-visible")) {
        cerrarModal(null);
      }
    });

    return {
      solicitar: abrirModal,
    };
  }

  function inicializarPanelBackups() {
    var panel = document.querySelector('[data-backup-panel="true"]');
    if (!panel) return;

    var modalPassword = crearControlModalPassword();

    var formGenerate = document.getElementById("formGenerateBackup");
    var formRestore = document.getElementById("formRestoreBackup");
    var formAutoConfig = document.getElementById("formAutoBackupConfig");
    var btnGenerate = document.getElementById("btnGenerateBackup");
    var btnRestore = document.getElementById("btnRestoreBackup");
    var btnDelete = document.getElementById("btnDeleteBackup");
    var btnSaveAutoConfig = document.getElementById("btnSaveAutoBackupConfig");
    var confirmPasswordGenerate = document.getElementById("confirmPasswordGenerate");
    var confirmPasswordRestore = document.getElementById("confirmPasswordRestore");
    var restoreActionInput = document.getElementById("restoreActionInput");

    var tableRows = panel.querySelectorAll(".backup-table tbody tr[data-backup-value]");

    function marcarFilaSeleccionada() {
      tableRows.forEach(function (row) {
        var radio = row.querySelector('input[type="radio"][name="backup_file"]');
        if (radio && radio.checked) {
          row.classList.add("selected");
        } else {
          row.classList.remove("selected");
        }
      });
    }

    tableRows.forEach(function (row) {
      row.addEventListener("click", function (event) {
        if (event.target && event.target.tagName === "INPUT") {
          marcarFilaSeleccionada();
          return;
        }

        var radio = row.querySelector('input[type="radio"][name="backup_file"]');
        if (!radio) return;
        radio.checked = true;
        marcarFilaSeleccionada();
      });
    });

    marcarFilaSeleccionada();

    function pedirContrasenaYEnviar(config) {
      return modalPassword.solicitar({
        title: config.modalTitle,
        subtitle: config.modalSubtitle,
        confirmText: config.modalConfirmText,
        variant: config.modalVariant,
        iconClass: config.modalIcon,
      }).then(function (password) {
        if (password === null || typeof password === "undefined") {
          return;
        }

        if (config.hiddenInput) {
          config.hiddenInput.value = password;
        }

        bloquearBoton(config.button, config.loadingText);
        config.form.submit();
      });
    }

    if (formGenerate) {
      formGenerate.addEventListener("submit", function (event) {
        event.preventDefault();

        useConfirm("Se va a generar una nueva copia de seguridad. ¿Deseas continuar?", {
          title: "Confirmar generación",
          confirmText: "Sí, generar",
          confirmClass: "cm-btn-success",
          confirmIcon: "fas fa-database",
        }).then(function (ok) {
          if (!ok) return;

          pedirContrasenaYEnviar({
            form: formGenerate,
            hiddenInput: confirmPasswordGenerate,
            button: btnGenerate,
            loadingText: "Generando...",
            modalTitle: "Autenticacion requerida",
            modalSubtitle: "Ingresa tu contraseña para generar una nueva copia.",
            modalConfirmText: "Generar copia",
            modalVariant: "success",
            modalIcon: "ri-lock-password-line",
          });
        });
      });
    }

    if (formRestore) {
      formRestore.addEventListener("submit", function (event) {
        event.preventDefault();

        var accion = "restaurar_backup";
        if (event.submitter && event.submitter.dataset && event.submitter.dataset.accion) {
          accion = event.submitter.dataset.accion;
        }

        if (restoreActionInput) {
          restoreActionInput.value = accion;
        }

        var backupFile = formRestore.querySelector('input[name="backup_file"]:checked');
        if (!backupFile || !backupFile.value) {
          useAlert("Selecciona un archivo de backup para continuar.", "warning");
          return;
        }

        var esEliminacion = accion === "eliminar_backup";
        var message = esEliminacion
          ? "Se eliminara la copia seleccionada de forma permanente. Esta accion no se puede deshacer."
          : "Vas a restaurar sobre la base principal. Esta accion puede sobrescribir datos actuales.";

        useConfirm(message, {
          title: esEliminacion ? "Confirmar eliminacion de backup" : "Confirmar restauracion principal",
          confirmText: esEliminacion ? "Si, eliminar" : "Si, restaurar",
          confirmClass: esEliminacion ? "cm-btn-danger" : "cm-btn-danger",
          confirmIcon: esEliminacion ? "fas fa-trash" : "fas fa-rotate-right",
        }).then(function (ok) {
          if (!ok) return;

          pedirContrasenaYEnviar({
            form: formRestore,
            hiddenInput: confirmPasswordRestore,
            button: esEliminacion ? btnDelete : btnRestore,
            loadingText: esEliminacion ? "Eliminando..." : "Restaurando...",
            modalTitle: "Validacion de seguridad",
            modalSubtitle: esEliminacion
              ? "Ingresa tu contraseña para eliminar la copia seleccionada."
              : "Ingresa tu contraseña para restaurar la base principal.",
            modalConfirmText: esEliminacion ? "Eliminar copia" : "Restaurar base",
            modalVariant: esEliminacion ? "danger" : "warning",
            modalIcon: esEliminacion ? "ri-delete-bin-6-line" : "ri-shield-check-line",
          });
        });
      });
    }

    if (formAutoConfig) {
      formAutoConfig.addEventListener("submit", function () {
        bloquearBoton(btnSaveAutoConfig, "Guardando...");
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", inicializarPanelBackups);
  } else {
    inicializarPanelBackups();
  }
})();
