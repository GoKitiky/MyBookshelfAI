use std::sync::Mutex;

use tauri::{AppHandle, Manager, RunEvent};
use tauri_plugin_shell::ShellExt;

const BACKEND_HOST: &str = "127.0.0.1";
const BACKEND_PORT: &str = "8315";
const BACKEND_SIDECAR_NAME: &str = "mybookshelf-backend";

struct BackendState {
  child: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
}

fn stop_backend(app: &AppHandle) {
  if let Some(state) = app.try_state::<BackendState>() {
    if let Ok(mut guard) = state.child.lock() {
      if let Some(child) = guard.take() {
        let _ = child.kill();
      }
    }
  }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  let mut builder = tauri::Builder::default().plugin(tauri_plugin_shell::init());

  if cfg!(debug_assertions) {
    builder = builder.plugin(
      tauri_plugin_log::Builder::default()
        .level(log::LevelFilter::Info)
        .build(),
    );
  }

  let app = builder
    .setup(|app| {
      let app_data_dir = app.path().app_data_dir()?;
      std::fs::create_dir_all(&app_data_dir)?;
      let data_dir_arg = app_data_dir.to_string_lossy().into_owned();

      let sidecar = app.shell().sidecar(BACKEND_SIDECAR_NAME)?;
      let args = vec![
        "--host".to_string(),
        BACKEND_HOST.to_string(),
        "--port".to_string(),
        BACKEND_PORT.to_string(),
        "--data-dir".to_string(),
        data_dir_arg,
      ];
      let (mut rx, child) = sidecar.args(args).spawn()?;
      tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
          match event {
            tauri_plugin_shell::process::CommandEvent::Error(line) => {
              eprintln!("[backend-sidecar] {line}");
            }
            tauri_plugin_shell::process::CommandEvent::Stderr(raw) => {
              let line = String::from_utf8_lossy(&raw);
              eprintln!("[backend-sidecar] {line}");
            }
            _ => {}
          }
        }
      });

      app.manage(BackendState {
        child: Mutex::new(Some(child)),
      });
      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("error while building tauri application");

  app.run(|app_handle, event| {
    if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
      stop_backend(app_handle);
    }
  });
}
