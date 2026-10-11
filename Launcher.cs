using System;
using System.Diagnostics;
using System.IO;
using System.Text;

namespace YizeLauncher
{
    class Program
    {
        static void Main(string[] args)
        {
            try
            {
                Console.OutputEncoding = Encoding.UTF8;
                Console.InputEncoding = Encoding.UTF8;
            }
            catch { }

            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            Directory.SetCurrentDirectory(baseDir);

            Console.ForegroundColor = ConsoleColor.Magenta;
            Console.WriteLine("======================================================================");
            Console.WriteLine("         ✦ [YIZE 3D] ASISTENTE VIRTUAL & COPILOTO AUTÓNOMA ✦          ");
            Console.WriteLine("======================================================================");
            Console.ResetColor();
            Console.WriteLine();

            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine("  ¿Cómo deseas interactuar con Yize?");
            Console.WriteLine();
            Console.WriteLine("  [1] Modo Voz Directo (Hablar por micrófono con Yize)  [Por Defecto]");
            Console.WriteLine("  [2] Modo Texto / Consola (Escribir en el teclado)");
            Console.WriteLine("  [3] Servidor Móvil PWA (Control desde el teléfono con código QR)");
            Console.WriteLine("  [4] Iniciar Todo (Modo Voz en PC + Servidor Móvil para Celular)");
            Console.WriteLine("======================================================================");
            Console.ResetColor();
            Console.WriteLine();

            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.Write("Presiona ENTER para iniciar [1] Modo Voz (o escribe 1, 2, 3, 4): ");
            Console.ResetColor();

            string opcion = Console.ReadLine();
            if (string.IsNullOrWhiteSpace(opcion)) opcion = "1";
            opcion = opcion.Trim();

            SafeClear();

            // Detectar intérprete de Python (entorno virtual o global)
            string pythonExe = "python";
            string venvPy = Path.Combine(baseDir, ".venv", "Scripts", "python.exe");
            if (File.Exists(venvPy))
            {
                pythonExe = venvPy;
            }

            try
            {
                if (opcion == "4")
                {
                    Console.ForegroundColor = ConsoleColor.Magenta;
                    Console.WriteLine("======================================================================");
                    Console.WriteLine("  INICIANDO YIZE EN MODO VOZ + SERVIDOR MÓVIL PWA");
                    Console.WriteLine("======================================================================");
                    Console.ResetColor();

                    RunProcessInteractive(pythonExe, "main.py --voz --con-movil", baseDir);
                }
                else if (opcion == "3")
                {
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("======================================================================");
                    Console.WriteLine("  INICIANDO SERVIDOR MÓVIL PWA — Escanea el QR con tu teléfono");
                    Console.WriteLine("======================================================================");
                    Console.ResetColor();

                    RunProcessInteractive(pythonExe, "mobile_server.py", baseDir);
                }
                else if (opcion == "2")
                {
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("======================================================================");
                    Console.WriteLine("  INICIANDO MODO TEXTO — Escribe tus preguntas u órdenes");
                    Console.WriteLine("======================================================================");
                    Console.ResetColor();

                    RunProcessInteractive(pythonExe, "main.py --texto", baseDir);
                }
                else
                {
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("======================================================================");
                    Console.WriteLine("  INICIANDO MODO VOZ DIRECTO — Háblale por micrófono a Yize");
                    Console.WriteLine("======================================================================");
                    Console.ResetColor();

                    RunProcessInteractive(pythonExe, "main.py --voz", baseDir);
                }
            }
            catch (Exception ex)
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("\n[Error ejecutando Yize]: " + ex.Message);
                Console.ResetColor();
                Console.WriteLine("\nPresiona cualquier tecla para salir...");
                SafeReadKey();
            }
        }

        static void SafeClear()
        {
            try { Console.Clear(); } catch { }
        }

        static void SafeReadKey()
        {
            try { Console.ReadKey(); } catch { }
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
