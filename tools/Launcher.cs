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
            try { Console.OutputEncoding = Encoding.UTF8; } catch { }
            try { Console.Title = "Yize 3D - Asistente Virtual"; } catch { }

            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            Directory.SetCurrentDirectory(baseDir);

            string pythonExe = "python";
            string mainPy = Path.Combine(baseDir, "main.py");

            if (!File.Exists(mainPy))
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("[Error] No se encontró main.py en: " + baseDir);
                Console.ResetColor();
                Console.WriteLine("Presiona una tecla para salir...");
                Console.ReadKey();
                return;
            }

            // Reenviar parámetros CLI recibidos hacia main.py
            string arguments = "\"" + mainPy + "\"";
            if (args != null && args.Length > 0)
            {
                arguments += " " + string.Join(" ", args);
            }

            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = arguments,
                WorkingDirectory = baseDir,
                UseShellExecute = false
            };

            try
            {
                using (Process p = Process.Start(psi))
                {
                    if (p != null)
                    {
                        p.WaitForExit();
                    }
                }
            }
            catch (Exception ex)
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("[Error iniciando Yize]: " + ex.Message);
                Console.ResetColor();
                Console.WriteLine("Presiona una tecla para salir...");
                Console.ReadKey();
            }
        }
    }
}