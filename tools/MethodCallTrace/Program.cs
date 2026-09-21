using System.Reflection;
using System.Reflection.Emit;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;

static string GetTypeDefinitionName(MetadataReader reader, TypeDefinitionHandle handle)
{
    var type = reader.GetTypeDefinition(handle);
    var ns = reader.GetString(type.Namespace);
    var name = reader.GetString(type.Name);
    return string.IsNullOrEmpty(ns) ? name : $"{ns}.{name}";
}

static string GetTypeReferenceName(MetadataReader reader, TypeReferenceHandle handle)
{
    var type = reader.GetTypeReference(handle);
    var ns = reader.GetString(type.Namespace);
    var name = reader.GetString(type.Name);
    return string.IsNullOrEmpty(ns) ? name : $"{ns}.{name}";
}

static string? GetMemberParentTypeName(MetadataReader reader, EntityHandle parent)
{
    return parent.Kind switch
    {
        HandleKind.TypeDefinition => GetTypeDefinitionName(reader, (TypeDefinitionHandle)parent),
        HandleKind.TypeReference => GetTypeReferenceName(reader, (TypeReferenceHandle)parent),
        _ => null
    };
}

static Dictionary<short, OpCode> BuildOpcodeMap()
{
    var map = new Dictionary<short, OpCode>();
    foreach (var field in typeof(OpCodes).GetFields(BindingFlags.Public | BindingFlags.Static))
    {
        if (field.GetValue(null) is OpCode op)
        {
            map[op.Value] = op;
        }
    }
    return map;
}

static int GetOperandSize(byte[] il, int operandStart, OperandType operandType)
{
    return operandType switch
    {
        OperandType.InlineNone => 0,
        OperandType.ShortInlineBrTarget => 1,
        OperandType.ShortInlineI => 1,
        OperandType.ShortInlineVar => 1,
        OperandType.InlineVar => 2,
        OperandType.InlineBrTarget => 4,
        OperandType.InlineField => 4,
        OperandType.InlineI => 4,
        OperandType.InlineMethod => 4,
        OperandType.InlineSig => 4,
        OperandType.InlineString => 4,
        OperandType.InlineTok => 4,
        OperandType.InlineType => 4,
        OperandType.ShortInlineR => 4,
        OperandType.InlineI8 => 8,
        OperandType.InlineR => 8,
        OperandType.InlineSwitch => GetSwitchSize(il, operandStart),
        _ => throw new NotSupportedException($"Unsupported operand type: {operandType}")
    };
}

static int GetSwitchSize(byte[] il, int operandStart)
{
    if (operandStart + 4 > il.Length)
    {
        return Math.Max(0, il.Length - operandStart);
    }

    var count = BitConverter.ToInt32(il, operandStart);
    if (count < 0)
    {
        return 4;
    }

    var size = 4L + 4L * count;
    var remaining = il.Length - operandStart;
    return (int)Math.Min(size, remaining);
}

if (args.Length != 3)
{
    Console.Error.WriteLine(
        "Usage: MethodCallTrace <assembly.dll> <target-type-name> <target-method-name>"
    );
    return 2;
}

var assemblyPath = Path.GetFullPath(args[0]);
var targetTypeName = args[1];
var targetMethodName = args[2];

if (!File.Exists(assemblyPath))
{
    Console.Error.WriteLine($"Assembly does not exist: {assemblyPath}");
    return 2;
}

using var stream = File.OpenRead(assemblyPath);
using var peReader = new PEReader(stream);

if (!peReader.HasMetadata)
{
    Console.Error.WriteLine($"Assembly has no managed metadata: {assemblyPath}");
    return 2;
}

var reader = peReader.GetMetadataReader();
var targetTokens = new HashSet<int>();

foreach (var methodHandle in reader.MethodDefinitions)
{
    var method = reader.GetMethodDefinition(methodHandle);
    if (!reader.GetString(method.Name).Equals(targetMethodName, StringComparison.Ordinal))
    {
        continue;
    }

    var owner = GetTypeDefinitionName(reader, method.GetDeclaringType());
    if (owner.Equals(targetTypeName, StringComparison.Ordinal)
        || owner.EndsWith("." + targetTypeName, StringComparison.Ordinal))
    {
        targetTokens.Add(MetadataTokens.GetToken(methodHandle));
    }
}

foreach (var memberHandle in reader.MemberReferences)
{
    var member = reader.GetMemberReference(memberHandle);
    if (!reader.GetString(member.Name).Equals(targetMethodName, StringComparison.Ordinal))
    {
        continue;
    }

    var owner = GetMemberParentTypeName(reader, member.Parent);
    if (owner != null
        && (owner.Equals(targetTypeName, StringComparison.Ordinal)
            || owner.EndsWith("." + targetTypeName, StringComparison.Ordinal)))
    {
        targetTokens.Add(MetadataTokens.GetToken(memberHandle));
    }
}

Console.WriteLine($"Assembly: {assemblyPath}");
Console.WriteLine($"Target: {targetTypeName}.{targetMethodName}");
Console.WriteLine(
    $"Resolved target tokens: {(targetTokens.Count == 0 ? "<none>" : string.Join(", ", targetTokens.Select(t => $"0x{t:X8}")))}"
);
Console.WriteLine();

if (targetTokens.Count == 0)
{
    Console.WriteLine("Call sites: 0");
    return 1;
}

var opcodeMap = BuildOpcodeMap();
var matches = new List<(string Owner, string Method, int MethodToken, int IlOffset, string Opcode, int TargetToken)>();

foreach (var methodHandle in reader.MethodDefinitions)
{
    var method = reader.GetMethodDefinition(methodHandle);
    if (method.RelativeVirtualAddress == 0)
    {
        continue;
    }

    MethodBodyBlock body;
    try
    {
        body = peReader.GetMethodBody(method.RelativeVirtualAddress);
    }
    catch (BadImageFormatException)
    {
        continue;
    }

    var il = body.GetILBytes();
    if (il == null || il.Length == 0)
    {
        continue;
    }

    var offset = 0;
    while (offset < il.Length)
    {
        var instructionOffset = offset;
        short opcodeValue;

        var first = il[offset++];
        if (first == 0xFE)
        {
            if (offset >= il.Length)
            {
                break;
            }
            opcodeValue = (short)(0xFE00 | il[offset++]);
        }
        else
        {
            opcodeValue = first;
        }

        if (!opcodeMap.TryGetValue(opcodeValue, out var opcode))
        {
            break;
        }

        var operandStart = offset;
        var operandSize = GetOperandSize(il, operandStart, opcode.OperandType);
        if (operandStart + operandSize > il.Length)
        {
            break;
        }

        if (opcode.OperandType == OperandType.InlineMethod && operandSize == 4)
        {
            var token = BitConverter.ToInt32(il, operandStart);
            if (targetTokens.Contains(token))
            {
                var owner = GetTypeDefinitionName(reader, method.GetDeclaringType());
                var methodName = reader.GetString(method.Name);
                matches.Add((
                    owner,
                    methodName,
                    MetadataTokens.GetToken(methodHandle),
                    instructionOffset,
                    opcode.Name ?? "<unknown>",
                    token
                ));
            }
        }

        offset += operandSize;
    }
}

foreach (var match in matches)
{
    Console.WriteLine(
        $"CALLER: {match.Owner}::{match.Method} methodToken=0x{match.MethodToken:X8} ilOffset=0x{match.IlOffset:X4} opcode={match.Opcode} targetToken=0x{match.TargetToken:X8}"
    );
}

Console.WriteLine();
Console.WriteLine($"Call sites: {matches.Count}");

return matches.Count > 0 ? 0 : 1;
