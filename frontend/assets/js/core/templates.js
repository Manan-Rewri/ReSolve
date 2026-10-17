/**
 * Starter code for the practice editor.
 *
 * Each template is LeetCode-shaped: a `Solution` type holding the method you
 * implement, plus a driver that reads your Standard input and prints the result.
 * Edit the driver to match whichever problem you are on.
 *
 * The standard input mirrors LeetCode's own sample layout, with the labels
 * stripped: the first line is the input array, the second line is the target.
 *   nums = [2,7,11,15]      ->  2 7 11 15
 *   n = 9                   ->  9
 *
 * The full standard library is available - the C++ and Java templates import
 * everything, so you can use any type without adding an include. Add your own
 * imports freely; Judge0 runs the file exactly as written.
 */

const CPP = `// Keep this #include line. Without it "vector" will not compile.
#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        // Your code here
        return {};
    }
};

// ---- driver: edit to match your problem ----
// line 1 = input array, line 2 = target
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string line;
    vector<int> nums;

    if (getline(cin, line)) {
        istringstream values(line);
        int value;
        while (values >> value) nums.push_back(value);
    }

    int target = 0;
    if (getline(cin, line)) target = stoi(line);

    vector<int> ans = Solution().twoSum(nums, target);

    for (int i = 0; i < (int)ans.size(); ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\\n';
    return 0;
}
`;

const C = `// Keep these #include lines. Without them scanf/printf will not compile.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// C has no classes or member functions, so the solution is a plain function.
// Two Sum needs a dynamic array, so a fixed output buffer is used here.
int twoSum(int* nums, int n, int target, int* out) {
    // Your code here
    return 0;
}

// ---- driver: edit to match your problem ----
// line 1 = input array, line 2 = target
int main() {
    char line[4096];
    int nums[256];
    int n = 0;
    int target = 0;

    if (fgets(line, sizeof(line), stdin)) {
        char *token = strtok(line, " \\t\\r\\n");
        while (token && n < 256) {
            nums[n++] = atoi(token);
            token = strtok(NULL, " \\t\\r\\n");
        }
    }

    if (fgets(line, sizeof(line), stdin)) target = atoi(line);

    int out[8] = {0};
    int size = twoSum(nums, n, target, out);

    for (int i = 0; i < size; i++) {
        if (i) printf(" ");
        printf("%d", out[i]);
    }
    printf("\\n");
    return 0;
}
`;

const PYTHON = `# Keep this import. Without it List[int] will raise NameError.
from typing import List


class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        # Your code here
        return []


# ---- driver: edit to match your problem ----
# line 1 = input array, line 2 = target
if __name__ == "__main__":
    import sys

    lines = [line for line in sys.stdin.read().splitlines() if line.strip()]
    nums = list(map(int, lines[0].split())) if lines else []
    target = int(lines[1]) if len(lines) > 1 else 0

    print(*Solution().twoSum(nums, target))
`;

const JAVA = `// Keep these imports. Without them Arrays and Scanner will not resolve.
import java.util.*;
import java.util.Scanner;

class Solution {
    public int[] twoSum(int[] nums, int target) {
        // Your code here
        return new int[0];
    }
}

// ---- driver: edit to match your problem ----
// line 1 = input array, line 2 = target
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);

        List<Integer> values = new ArrayList<>();
        if (sc.hasNextLine()) {
            for (String part : sc.nextLine().trim().split("\\\\s+")) {
                if (!part.isEmpty()) values.add(Integer.parseInt(part));
            }
        }

        int target = sc.hasNextLine() ? Integer.parseInt(sc.nextLine().trim()) : 0;

        int[] nums = new int[values.size()];
        for (int i = 0; i < nums.length; i++) nums[i] = values.get(i);

        int[] ans = new Solution().twoSum(nums, target);

        StringBuilder out = new StringBuilder();
        for (int i = 0; i < ans.length; i++) {
            if (i > 0) out.append(' ');
            out.append(ans[i]);
        }
        System.out.println(out);
    }
}
`;

const JAVASCRIPT = `// Keep the require() below - it is what reads your Standard input.
class Solution {
  twoSum(nums, target) {
    // Your code here
    return [];
  }
}

// ---- driver: edit to match your problem ----
// line 1 = input array, line 2 = target
const fs = require("fs");

const lines = fs
  .readFileSync(0, "utf-8")
  .split(/\\r?\\n/)
  .filter((line) => line.trim());

const nums = lines[0] ? lines[0].trim().split(/\\s+/).map(Number) : [];
const target = lines[1] ? Number(lines[1].trim()) : 0;

console.log(...new Solution().twoSum(nums, target));
`;

export const LANGUAGE_TEMPLATES = {
  cpp: CPP,
  c: C,
  python: PYTHON,
  java: JAVA,
  javascript: JAVASCRIPT,
};

export function templateFor(languageId) {
  return LANGUAGE_TEMPLATES[languageId] ?? CPP;
}

/**
 * Picks the editor's starting code.
 *
 * When the backend could drive this problem's signature it sends LeetCode's own
 * stub plus a generated driver, so the user only writes the method body. Any
 * other language falls back to the generic template, which is runnable but is
 * not the LeetCode shape.
 */
export function starterFor(problem, languageId) {
  const generated = problem?.starters?.[languageId];
  return typeof generated === "string" && generated.trim()
    ? generated
    : templateFor(languageId);
}

/**
 * Converts LeetCode's labelled sample into the raw layout the drivers read,
 * keeping one array/target per line:
 *   "nums = [2,7,11,15]\\nn = 9"  ->  "2 7 11 15\\n9"
 */
export function sampleToStdin(sample) {
  if (!sample) return "";
  return sample
    .split(/\r?\n/)
    .map((line) =>
      line
        .replace(/[A-Za-z_]\w*\s*=\s*/g, "")
        .replace(/[\[\]{}(),"]/g, " ")
        .replace(/\s+/g, " ")
        .trim()
    )
    .filter(Boolean)
    .join("\n");
}