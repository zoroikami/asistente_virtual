// Tauri v2 main entry point
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    yize_overlay_lib::run()
}
