use std::net::UdpSocket;
use tauri::{Emitter, Manager}; // <-- Add this to the top of your file!

#[tauri::command]
fn get_local_ip() -> String {
    // The "UDP Routing" trick to perfectly bypass virtual networks/VPNs
    if let Ok(socket) = UdpSocket::bind("0.0.0.0:0") {
        if socket.connect("8.8.8.8:80").is_ok() {
            if let Ok(addr) = socket.local_addr() {
                return addr.ip().to_string();
            }
        }
    }
    "127.0.0.1".to_string()
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

#[tauri::command]
#[allow(dead_code)]
fn close_current_window(window: tauri::Window) {
    let _ = window.close();
}

#[tauri::command]
fn close_details_window(app: tauri::AppHandle, label: String) {
    if let Some(window) = app.get_webview_window(&label) {
        let _ = window.close();
    }
}

#[tauri::command]
async fn open_details_window(
    app: tauri::AppHandle,
    serial: i32,
    payload: serde_json::Value,
) -> Result<(), String> {
    let label = format!("details-{}", serial);
    let url = format!("/#/details/{}", serial);

    if let Some(win) = app.get_webview_window(&label) {
        let _ = win.set_focus();
        return Ok(());
    }

    let window = tauri::WebviewWindowBuilder::new(&app, &label, tauri::WebviewUrl::App(url.into()))
        .title(format!("Details - {}", serial))
        .inner_size(900.0, 700.0)
        .center()
        .build()
        .map_err(|e| e.to_string())?;

    tauri::async_runtime::spawn(async move {
        tokio::time::sleep(std::time::Duration::from_millis(250)).await;
        let _ = window.emit("catalogue:selected-item", payload);
    });

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            open_details_window,
            close_current_window,
            close_details_window,
            get_local_ip // Hooked up right here, so it's no longer "dead code"!
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
