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
        HandleKind.TypeSpecification => "TypeSpecification",
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

static string GetOwnerName(MetadataReader reader, EntityHandle owner)
{
    return owner.Kind switch
    {
        HandleKind.TypeDefinition =>
            GetTypeDefinitionName(reader, (TypeDefinitionHandle)owner),
        HandleKind.MethodDefinition =>
            $"{GetTypeDefinitionName(reader, reader.GetMethodDefinition((MethodDefinitionHandle)owner).GetDeclaringType())}::{reader.GetString(reader.GetMethodDefinition((MethodDefinitionHandle)owner).Name)}",
        HandleKind.FieldDefinition =>
            $"Field:{MetadataTokens.GetToken(owner):X8}",
        HandleKind.PropertyDefinition =>
            $"Property:{MetadataTokens.GetToken(owner):X8}",
        _ => $"{owner.Kind}:{MetadataTokens.GetToken(owner):X8}"
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

if (args.Length < 2 || args.Length > 4)
{
    Console.Error.WriteLine(
        "Usage: MetadataTrace <assembly.dll> <target-type-name> [attribute-type-name|*] [--matching-only]"
    );
    return 2;
}

var assemblyPath = Path.GetFullPath(args[0]);
var targetTypeName = args[1];
var attributeTypeName = args.Length >= 3 ? args[2] : "AchUnlockOnComplete";
var matchingOnly = args.Length == 4 && args[3] == "--matching-only";

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
Console.WriteLine($"Matching only: {matchingOnly}");
Console.WriteLine();

var matchingTypes = new List<TypeDefinitionHandle>();
foreach (var typeHandle in reader.TypeDefinitions)
{
    var fullName = GetTypeDefinitionName(reader, typeHandle);
    var simpleName = reader.GetString(reader.GetTypeDefinition(typeHandle).Name);
    if (fullName.Equals(targetTypeName, StringComparison.Ordinal)
        || simpleName.Equals(targetTypeName, StringComparison.Ordinal)
        || fullName.Contains(targetTypeName, StringComparison.Ordinal))
    {
        matchingTypes.Add(typeHandle);
    }
}

Console.WriteLine("=== TARGET TYPE DEFINITIONS ===");
if (matchingTypes.Count == 0)
{
    Console.WriteLine("No matching type definition found in this assembly.");
}
else
{
    foreach (var typeHandle in matchingTypes)
    {
        var type = reader.GetTypeDefinition(typeHandle);
        Console.WriteLine($"Type: {GetTypeDefinitionName(reader, typeHandle)}");
        Console.WriteLine($"Token: 0x{MetadataTokens.GetToken(typeHandle):X8}");
        Console.WriteLine($"Base type: {(type.BaseType.IsNil ? "<none>" : GetTypeName(reader, type.BaseType))}");

        var interfaces = new List<string>();
        foreach (var interfaceHandle in type.GetInterfaceImplementations())
        {
            var implementation = reader.GetInterfaceImplementation(interfaceHandle);
            interfaces.Add(GetTypeName(reader, implementation.Interface));
        }
        Console.WriteLine($"Interfaces: {(interfaces.Count == 0 ? "<none>" : string.Join(", ", interfaces))}");

        var ownAttributes = new List<string>();
        foreach (var attributeHandle in type.GetCustomAttributes())
        {
            ownAttributes.Add(GetAttributeTypeName(reader, reader.GetCustomAttribute(attributeHandle)));
        }
        Console.WriteLine($"Type attributes: {(ownAttributes.Count == 0 ? "<none>" : string.Join(", ", ownAttributes))}");
        Console.WriteLine();
    }
}

Console.WriteLine("=== CUSTOM ATTRIBUTE TRACE ===");

var filteredAttributeCount = 0;
var targetMatchCount = 0;

foreach (var handle in reader.CustomAttributes)
{
    var attribute = reader.GetCustomAttribute(handle);
    var attributeType = GetAttributeTypeName(reader, attribute);

    if (attributeTypeName != "*"
        && !attributeType.Contains(attributeTypeName, StringComparison.Ordinal))
    {
        continue;
    }

    filteredAttributeCount++;

    var blob = reader.GetBlobBytes(attribute.Value);
    var containsTarget = BlobContains(blob, targetTypeName);
    if (matchingOnly && !containsTarget)
    {
        continue;
    }

    var owner = GetOwnerName(reader, attribute.Parent);
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

Console.WriteLine($"Filtered attribute instances: {filteredAttributeCount}");
Console.WriteLine($"Target matches: {targetMatchCount}");

return targetMatchCount > 0 ? 0 : 1;
