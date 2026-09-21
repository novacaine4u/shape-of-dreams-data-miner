using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Text;

static string GetTypeName(MetadataReader reader, EntityHandle handle)
{
    return handle.Kind switch
    {
        HandleKind.TypeDefinition => GetTypeDefinitionName(reader, (TypeDefinitionHandle)handle),
        HandleKind.TypeReference => GetTypeReferenceName(reader, (TypeReferenceHandle)handle),
        _ => handle.Kind.ToString()
    };
}

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

static string GetAttributeTypeName(MetadataReader reader, CustomAttribute attribute)
{
    return attribute.Constructor.Kind switch
    {
        HandleKind.MethodDefinition =>
            GetTypeDefinitionName(
                reader,
                reader.GetMethodDefinition((MethodDefinitionHandle)attribute.Constructor)
                    .GetDeclaringType()
            ),

        HandleKind.MemberReference =>
            GetTypeName(
                reader,
                reader.GetMemberReference((MemberReferenceHandle)attribute.Constructor).Parent
            ),

        _ => attribute.Constructor.Kind.ToString()
    };
}

static bool BlobContains(byte[] blob, string term)
{
    var needle = Encoding.UTF8.GetBytes(term);
    if (needle.Length == 0 || blob.Length < needle.Length)
    {
        return false;
    }

    for (var i = 0; i <= blob.Length - needle.Length; i++)
    {
        var matched = true;
        for (var j = 0; j < needle.Length; j++)
        {
            if (blob[i + j] != needle[j])
            {
                matched = false;
                break;
            }
        }

        if (matched)
        {
            return true;
        }
    }

    return false;
}

static IEnumerable<string> ExtractPrintableRuns(byte[] bytes, int minLength = 4)
{
    var start = -1;

    for (var i = 0; i <= bytes.Length; i++)
    {
        var printable = i < bytes.Length && bytes[i] >= 0x20 && bytes[i] <= 0x7e;

        if (printable && start < 0)
        {
            start = i;
        }

        if (!printable && start >= 0)
        {
            var length = i - start;
            if (length >= minLength)
            {
                yield return Encoding.ASCII.GetString(bytes, start, length);
            }

            start = -1;
        }
    }
}

if (args.Length < 2 || args.Length > 3)
{
    Console.Error.WriteLine(
        "Usage: MetadataTrace <assembly.dll> <target-type-name> [attribute-type-name]"
    );
    return 2;
}

var assemblyPath = Path.GetFullPath(args[0]);
var targetTypeName = args[1];
var attributeTypeName = args.Length == 3 ? args[2] : "AchUnlockOnComplete";

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

Console.WriteLine($"Assembly: {assemblyPath}");
Console.WriteLine($"Target type: {targetTypeName}");
Console.WriteLine($"Attribute type filter: {attributeTypeName}");
Console.WriteLine();

var attributeCount = 0;
var targetMatchCount = 0;

foreach (var handle in reader.CustomAttributes)
{
    var attribute = reader.GetCustomAttribute(handle);
    var attributeType = GetAttributeTypeName(reader, attribute);

    if (!attributeType.Contains(attributeTypeName, StringComparison.Ordinal))
    {
        continue;
    }

    attributeCount++;

    var owner = attribute.Parent.Kind == HandleKind.TypeDefinition
        ? GetTypeDefinitionName(reader, (TypeDefinitionHandle)attribute.Parent)
        : $"{attribute.Parent.Kind}:{MetadataTokens.GetToken(attribute.Parent):X8}";

    var blob = reader.GetBlobBytes(attribute.Value);
    var containsTarget = BlobContains(blob, targetTypeName);
    var printable = string.Join(" | ", ExtractPrintableRuns(blob));

    Console.WriteLine($"Attribute owner: {owner}");
    Console.WriteLine($"Attribute type: {attributeType}");
    Console.WriteLine($"Contains target bytes: {containsTarget}");
    if (!string.IsNullOrEmpty(printable))
    {
        Console.WriteLine($"Printable blob text: {printable}");
    }
    Console.WriteLine();

    if (containsTarget)
    {
        targetMatchCount++;
        Console.WriteLine($"MATCH: {owner} -> {targetTypeName}");
        Console.WriteLine();
    }
}

Console.WriteLine($"Matching attribute instances: {attributeCount}");
Console.WriteLine($"Target matches: {targetMatchCount}");

return targetMatchCount > 0 ? 0 : 1;
