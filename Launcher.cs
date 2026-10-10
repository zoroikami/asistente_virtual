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
                Console.Title = "Yize 3D - Asistente Virtual y Copiloto de Escritorio";
            }
            catch { }

            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            Directory.SetCurrentDirectory(baseDir);

            Console.ForegroundColor = ConsoleColor.Magenta;
            Console.WriteLine("======================================================================");
            Console.WriteLine("         [YIZE 3D] ASISTENTE VIRTUAL Y VTUBER DE ESCRITORIO           ");
            Console.WriteLine("======================================================================");
            Console.ResetColor();
            Console.WriteLine();

            // 1. Iniciar Overlay 3D si no está abierto
            EnsureOverlayRunning(baseDir);

            Console.WriteLine();
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine("======================================================================");
            Console.WriteLine("  Como prefieres interactuar con Yize?");
            Console.WriteLine();
            Console.WriteLine("  [1] Modo Texto / Consola (Escribir en teclado - Recomendado)");
            Console.WriteLine("  [2] Modo Voz (Hablarle por microfono continuamente)");
            Console.WriteLine("  [3] Servidor Movil (Controlar desde tu celular con codigo QR)");
            Console.WriteLine("  [4] Iniciar Todo (Asistente en PC + Servidor Movil para Celular)");
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
                    Console.WriteLine("[*] Iniciando Servidor Movil en segundo plano...");
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
                    Console.WriteLine("  INICIANDO MODO TEXTO EN PC - Escribe tus preguntas u ordenes");
                    Console.WriteLine("======================================================================");
                    Console.ResetColor();

                    RunProcessInteractive(pythonExe, "main.py --texto", baseDir);
                }
                else if (opcion == "3")
                {
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("======================================================================");
                    Console.WriteLine("  INICIANDO SERVIDOR MOVIL - Escanea el QR con tu telefono");
                    Console.WriteLine("======================================================================");
                    Console.ResetColor();

                    RunProcessInteractive(pythonExe, "mobile_server.py", baseDir);
                }
                else if (opcion == "2")
                {
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("======================================================================");
                    Console.WriteLine("  INICIANDO MODO VOZ - Hablale por microfono a Yize");
                    Console.WriteLine("======================================================================");
                    Console.ResetColor();

                    RunProcessInteractive(pythonExe, "main.py", baseDir);
                }
                else
                {
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("======================================================================");
                    Console.WriteLine("  INICIANDO MODO TEXTO - Escribe tus preguntas u ordenes");
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
                    Console.WriteLine("[OK] Yize 3D Overlay ya esta activa en tu escritorio.");
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
                    Console.WriteLine("[OK] Yize 3D cargada correctamente.");
                    Console.ResetColor();
                }
                else
                {
                    Console.ForegroundColor = ConsoleColor.Yellow;
                    Console.WriteLine("[~] Overlay no encontrado en yize_overlay. Se iniciara en modo consola.");
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