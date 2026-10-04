// Exports {"Qualified::Name": [rva, ...]} for every non-external function of the current program, for civ6-frida-live (--symbols FILE).
// RVA = entry point minus the program's image base. Names Ghidra generated itself (FUN_xxxx, thunk stubs) are skipped.
// Run:  analyzeHeadless <projectDir> <projectName> -process <programName> -noanalysis -readOnly -scriptPath <dir with this file> -postScript ExportSymbols.java out.json
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.LinkedHashMap;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class ExportSymbols extends GhidraScript {
  @Override
  public void run() throws Exception {
    String out = getScriptArgs()[0];
    long base = currentProgram.getImageBase().getOffset();
    Map<String, List<Long>> map = new LinkedHashMap<>();
    for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
      if (f.isExternal() || f.isThunk()) continue;
      String name = f.getName(true);
      if (name.startsWith("FUN_") || name.contains("::FUN_")) continue;
      map.computeIfAbsent(name, k -> new ArrayList<>()).add(f.getEntryPoint().getOffset() - base);
    }
    try (PrintWriter w = new PrintWriter(new BufferedWriter(new FileWriter(out), 1 << 20))) {
      w.print("{");
      boolean first = true;
      for (Map.Entry<String, List<Long>> e : map.entrySet()) {
        if (!first) w.print(",");
        first = false;
        w.print("\n\"" + e.getKey().replace("\\", "\\\\").replace("\"", "\\\"") + "\":[");
        for (int i = 0; i < e.getValue().size(); i++) w.print((i > 0 ? "," : "") + e.getValue().get(i));
        w.print("]");
      }
      w.print("\n}\n");
    }
    println("exported " + map.size() + " names");
  }
}
