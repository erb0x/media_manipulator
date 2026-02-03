use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Enable logging in debug mode
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Spawn the backend sidecar in production
            #[cfg(not(debug_assertions))]
            {
                use tauri_plugin_shell::ShellExt;
                
                let sidecar = app
                    .shell()
                    .sidecar("media-organizer-backend")
                    .expect("Failed to create sidecar command");
                
                let (mut _rx, _child) = sidecar
                    .spawn()
                    .expect("Failed to spawn backend sidecar");
                
                log::info!("Backend sidecar started");
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
