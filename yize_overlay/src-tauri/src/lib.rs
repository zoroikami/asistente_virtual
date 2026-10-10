// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, WebviewWindow};

#[tauri::command]
fn set_click_through(window: WebviewWindow, enabled: bool) {
    let _ = window.set_ignore_cursor_events(enabled);
}

#[tauri::command]
fn set_position(window: WebviewWindow, x: f64, y: f64) {
    let _ = window.set_position(tauri::PhysicalPosition::new(x as i32, y as i32));
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();

            // Hacer la ventana siempre visible (encima de todo)
            window.set_always_on_top(true)?;

            // En Windows: quitar de la barra de tareas
            #[cfg(target_os = "windows")]
            {
                use tauri::PhysicalSize;
                // La ventana ya tiene decorations:false en config
                // set_skip_taskbar está en tauri 2 como plugin experimental
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            set_click_through,
            set_position,
        ])
        .run(tauri::generate_context!())
        .expect("error running Yize overlay");
}
