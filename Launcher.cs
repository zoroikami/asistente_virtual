using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;

namespace YizeLauncher
{
    class Program
    {
        static void Main(string[] args)
        {
            try
            {
                Console.OutputEncoding = Encoding.UTF8;
            }
            catch { }

            try
            {
                Console.Title = "âœ¦ Yize 3D â€” Asistente Virtual y Copiloto âœ¦";
            }
            catch { }

            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            Directory.SetCurrentDirectory(baseDir);

            Console.ForegroundColor = ConsoleColor.Magenta;
            Console.WriteLine("======================================================================");
            Console.WriteLine("         âœ¦  YIZE 3D â€” ASISTENTE VIRTUAL Y VTUBER DE ESCRITORIO  âœ¦      ");
            Console.WriteLine("======================================================================");
            Console.ResetColor();
            Console.WriteLine();

            // 1. Iniciar Overlay 3D si no estÃ¡ abierto
            EnsureOverlayRunning(baseDir);

            Console.WriteLine();
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine("======================================================================");
            Console.WriteLine("  Â¿CÃ³mo prefieres interactuar con Yize?");
            Console.WriteLine();
            Console.WriteLine("  [1] Modo Texto / Consola (Escribir en teclado â€” Recomendado)");
            Console.WriteLine("  [2] Modo Voz (Hablarle por micrÃ³fono continuamente)");
            Console.WriteLine("  [3] Servidor MÃ³vil (Controlar desde tu celular con cÃ³digo QR)");
            Console.WriteLine("  [4] Iniciar Todo (Asistente en PC + Servidor MÃ³vil para Celular)");
            Console.WriteLine("======================================================================");
            Console.ResetColor();
            Console.WriteLine();

            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.Write("Presiona ENTER para iniciar [1] (o escribe 1, 2, 3, 4): ");
            Console.ResetColor();

            string opcion = Console.ReadLine();
            if (string.IsNullOrWhiteSpace(opcion)) opcion = "1";
            opcion = opcion.Trim();

            SafeClear();

            string pythonExe = "python";

            try
            {
                if (opcion == "4")
                {
                    Console.ForegroundColor = ConsoleColor.Magenta;
                    Console.WriteLine("[*] Iniciando Servidor MÃ³vil en segundo plano...");
                    Console.ResetColor();

                    ProcessStartInfo srvInfo = new ProcessStartInfo
                    {
                        FileName = "cmd.exe",
                        Arguments = "/k chcp 65001 >nul && \"" + pythonExe + "\" mobile_server.py",
                        WorkingDirectory = baseDir,
                        UseShellExecute = true
                    };
                    Process.Start(srvInfo);

                    Thread.Sleep(1500);

                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("======================================================================");
                    Console.WriteLine("  INICIANDO MODO TEXTO EN PC â€” Escribe tus preguntas u Ã³rdenes");
                    Console.WriteLine("======================================================================");
                    Console.ResetColor();

                    RunProcessInteractive(pythonExe, "main.py --texto", baseDir);
                }
                else if (opcion == "3")
                {
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("======================================================================");
                    Console.WriteLine("  INICIANDO SERVIDOR MÃ“VIL â€” Escanea el QR con tu telÃ©fono");
                    Console.WriteLine("======================================================================");
                    Console.ResetColor();

                    RunProcessInteractive(pythonExe, "mobile_server.py", baseDir);
                }
                else if (opcion == "2")
                {
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("======================================================================");
                    Console.WriteLine("  INICIANDO MODO VOZ â€” HÃ¡blale por micrÃ³fono a Yize");
                    Console.WriteLine("======================================================================");
                    Console.ResetColor();

                    RunProcessInteractive(pythonExe, "main.py", baseDir);
                }
                else
                {
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("======================================================================");
                    Console.WriteLine("  INICIANDO MODO TEXTO â€” Escribe tus preguntas u Ã³rdenes");
                    Console.WriteLine("======================================================================");
                    Console.ResetColor();

                    RunProcessInteractive(pythonExe, "main.py --texto", baseDir);
                }
            }
            catch (Exception ex)
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("\n[Error ejecutando Yize]: " + ex.Message);
                Console.ResetColor();
            }

            Console.WriteLine("\nPresiona cualquier tecla para salir...");
            SafeReadKey();
        }

        static void SafeClear()
        {
            try { Console.Clear(); } catch { }
        }

        static void SafeReadKey()
        {
            try { Console.ReadKey(); } catch { }
        }

        static void EnsureOverlayRunning(string baseDir)
        {
            try
            {
                Process[] procs = Process.GetProcessesByName("electron");
                if (procs.Length > 0)
                {
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("[âœ“] Yize 3D Overlay ya estÃ¡ activa en tu escritorio.");
                    Console.ResetColor();
                    return;
                }

                string electronExe = Path.Combine(baseDir, "yize_overlay", "node_modules", "electron", "dist", "electron.exe");
                string mainCjs = Path.Combine(baseDir, "yize_overlay", "electron-main.cjs");

                if (File.Exists(electronExe) && File.Exists(mainCjs))
                {
                    Console.ForegroundColor = ConsoleColor.Cyan;
                    Console.WriteLine("[*] Cargando a Yize 3D sobre tu pantalla...");
                    Console.ResetColor();

                    ProcessStartInfo psi = new ProcessStartInfo
                    {
                        FileName = electronExe,
                        Arguments = "\"" + mainCjs + "\"",
                        WorkingDirectory = Path.Combine(baseDir, "yize_overlay"),
                        UseShellExecute = true
                    };
                    Process.Start(psi);
                    Thread.Sleep(1500);

                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("[âœ“] Yize 3D cargada correctamente.");
                    Console.ResetColor();
                }
                else
                {
                    Console.ForegroundColor = ConsoleColor.Yellow;
                    Console.WriteLine("[~] Overlay no encontrado en yize_overlay. Se iniciarÃ¡ en modo consola.");
                    Console.ResetColor();
                }
            }
            catch (Exception ex)
            {
                Console.ForegroundColor = ConsoleColor.Yellow;
                Console.WriteLine("[~] Aviso cargando overlay: " + ex.Message);
                Console.ResetColor();
            }
        }

        static void RunProcessInteractive(string exe, string args, string workingDir)
        {
            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = exe,
                Arguments = args,
                WorkingDirectory = workingDir,
                UseShellExecute = false
            };

            using (Process p = Process.Start(psi))
            {
                if (p != null)
                {
                    p.WaitForExit();
                }
            }
        }
    }
}